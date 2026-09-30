package com.project.backend.services.implementations;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.project.backend.clients.AgentClient;
import com.project.backend.dtos.AnswerFeedbackRequestDto;
import com.project.backend.dtos.ChatMessageDto;
import com.project.backend.dtos.ChatThreadDto;
import com.project.backend.dtos.LordsMobileChatRequestDto;
import com.project.backend.dtos.LordsMobileChatResponseDto;
import com.project.backend.dtos.PlayerProfileDto;
import com.project.backend.entities.AnswerFeedback;
import com.project.backend.entities.ChatMessage;
import com.project.backend.entities.ChatThread;
import com.project.backend.entities.PlayerProfile;
import com.project.backend.entities.User;
import com.project.backend.exceptions.DownstreamServiceException;
import com.project.backend.exceptions.ResourceNotFoundException;
import com.project.backend.repositories.AnswerFeedbackRepository;
import com.project.backend.repositories.ChatMessageRepository;
import com.project.backend.repositories.ChatThreadRepository;
import com.project.backend.repositories.PlayerProfileRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class LordsMobileService {

    private static final TypeReference<Map<String, Object>> PLAYER_CONTEXT_TYPE = new TypeReference<>() {
    };

    private final ChatThreadRepository threadRepository;
    private final ChatMessageRepository messageRepository;
    private final AnswerFeedbackRepository feedbackRepository;
    private final PlayerProfileRepository profileRepository;
    private final ProfileVersionService profileVersionService;
    private final AgentClient agentClient;
    private final ChatRateLimitService rateLimitService;
    private final ObjectMapper objectMapper;

    public LordsMobileChatResponseDto chat(User user, LordsMobileChatRequestDto request) {
        PlayerProfile profile = getOrCreateProfile(user);
        if (!profile.isSetupCompleted()) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_REQUIRED,
                    "Configurez votre profil dans Settings avant d’envoyer une question.");
        }
        rateLimitService.check(user.getId());
        String language = profile.getLanguage();
        String gameVersion = "specific".equals(profile.getVersionMode()) ? profile.getGameVersion() : null;

        ChatThread thread = request.getThreadId() == null
                ? createThread(user, request.getMessage(), language, gameVersion)
                : ownedThread(request.getThreadId(), user);

        ChatMessage userMessage = ChatMessage.builder()
                .thread(thread)
                .role(ChatMessage.Role.USER)
                .content(request.getMessage().trim())
                .gameVersion(gameVersion)
                .sources(JsonNodeFactory.instance.arrayNode())
                .build();
        messageRepository.save(userMessage);

        Map<String, Object> context = buildPlayerContext(profile, request.getPlayerContext());
        AgentClient.AgentChatResponse agentResponse = agentClient.chat(
                new AgentClient.AgentChatRequest(
                        request.getMessage().trim(),
                        thread.getId().toString(),
                        user.getId().toString(),
                        language,
                        gameVersion,
                        context,
                        firstNonBlank(request.getSearchType(), "hybrid"),
                        request.getTopK() == null ? 8 : request.getTopK()));

        if (!agentResponse.readOnly()) {
            throw new DownstreamServiceException(
                    HttpStatus.BAD_GATEWAY, "Agent response did not confirm read-only mode");
        }

        JsonNode sources = agentResponse.sources() == null
                ? JsonNodeFactory.instance.arrayNode()
                : agentResponse.sources();
        ChatMessage assistantMessage = ChatMessage.builder()
                .thread(thread)
                .role(ChatMessage.Role.ASSISTANT)
                .content(agentResponse.response())
                .confidence(BigDecimal.valueOf(agentResponse.confidence()).setScale(4, RoundingMode.HALF_UP))
                .sources(sources)
                .intent(agentResponse.intent())
                .gameVersion(agentResponse.gameVersion())
                .generationMode(agentResponse.generationMode())
                .build();
        assistantMessage = messageRepository.save(assistantMessage);

        thread.setLanguage(agentResponse.language());
        thread.setGameVersion(agentResponse.gameVersion());
        threadRepository.save(thread);

        return LordsMobileChatResponseDto.builder()
                .threadId(thread.getId())
                .messageId(assistantMessage.getId())
                .response(agentResponse.response())
                .intent(agentResponse.intent())
                .language(agentResponse.language())
                .gameVersion(agentResponse.gameVersion())
                .sources(sources)
                .confidence(agentResponse.confidence())
                .needsClarification(agentResponse.needsClarification())
                .searchType(agentResponse.searchType())
                .rewrittenQueries(agentResponse.rewrittenQueries())
                .generationMode(agentResponse.generationMode())
                .readOnly(true)
                .build();
    }

    @Transactional(readOnly = true)
    public List<ChatThreadDto> listThreads(User user) {
        return threadRepository.findAllByUserOrderByUpdatedAtDesc(user).stream()
                .map(thread -> toThreadDto(thread, null))
                .toList();
    }

    @Transactional(readOnly = true)
    public ChatThreadDto getThread(User user, UUID threadId) {
        ChatThread thread = ownedThread(threadId, user);
        List<ChatMessageDto> messages = messageRepository.findAllByThreadOrderByCreatedAtAsc(thread).stream()
                .map(this::toMessageDto)
                .toList();
        return toThreadDto(thread, messages);
    }

    @Transactional
    public void deleteThread(User user, UUID threadId) {
        ChatThread thread = ownedThread(threadId, user);
        agentClient.deleteThread(threadId.toString());
        feedbackRepository.deleteAllByMessageThread(thread);
        messageRepository.deleteAllByThread(thread);
        threadRepository.delete(thread);
    }

    @Transactional
    public void saveFeedback(User user, UUID messageId, AnswerFeedbackRequestDto request) {
        ChatMessage message = messageRepository.findByIdAndThreadUser(messageId, user)
                .orElseThrow(() -> new ResourceNotFoundException("Assistant message not found"));
        if (message.getRole() != ChatMessage.Role.ASSISTANT) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Feedback is only accepted for assistant messages");
        }
        AnswerFeedback feedback = feedbackRepository.findByMessageAndUser(message, user)
                .orElseGet(() -> AnswerFeedback.builder().message(message).user(user).build());
        feedback.setRating(AnswerFeedback.Rating.valueOf(request.getRating()));
        feedback.setComment(request.getComment());
        feedbackRepository.save(feedback);
    }

    @Transactional
    public PlayerProfileDto getProfile(User user) {
        return toProfileDto(getOrCreateProfile(user));
    }

    @Transactional
    public PlayerProfileDto updateProfile(User user, PlayerProfileDto request) {
        String version = blankToNull(request.getGameVersion());
        if ("specific".equals(request.getVersionMode())) {
            if (version == null || !profileVersionService.supportedVersions().contains(version)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                        "Choisissez une version documentée ou l’option version inconnue.");
            }
        } else if (!"unknown".equals(request.getVersionMode()) || version != null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Choix de version incohérent.");
        }
        PlayerProfile profile = getOrCreateProfile(user);
        profile.setResponseLength(request.getResponseLength());
        profile.setVersionMode(request.getVersionMode());
        profile.setSetupCompleted(true);
        profile.setLanguage(firstNonBlank(request.getLanguage(), "fr"));
        profile.setGameVersion(blankToNull(request.getGameVersion()));
        profile.setPlayerLevel(blankToNull(request.getPlayerLevel()));
        profile.setPlayStyle(blankToNull(request.getPlayStyle()));
        profile.setKingdom(blankToNull(request.getKingdom()));
        profile.setAdditionalContext(request.getAdditionalContext());
        return toProfileDto(profileRepository.save(profile));
    }

    private PlayerProfile getOrCreateProfile(User user) {
        return profileRepository.findByUser(user).orElseGet(() -> profileRepository.save(
                PlayerProfile.builder()
                        .user(user)
                        .language("fr")
                        .additionalContext(JsonNodeFactory.instance.objectNode())
                        .build()));
    }

    private ChatThread createThread(User user, String message, String language, String gameVersion) {
        String normalized = message.trim().replaceAll("\\s+", " ");
        String title = normalized.length() <= 80 ? normalized : normalized.substring(0, 77) + "...";
        return threadRepository.save(ChatThread.builder()
                .user(user)
                .title(title)
                .language(language)
                .gameVersion(gameVersion)
                .build());
    }

    private ChatThread ownedThread(UUID threadId, User user) {
        return threadRepository.findByIdAndUser(threadId, user)
                .orElseThrow(() -> new ResourceNotFoundException("Conversation not found"));
    }

    private Map<String, Object> buildPlayerContext(PlayerProfile profile, Map<String, Object> overrides) {
        Map<String, Object> context = new LinkedHashMap<>();
        putIfPresent(context, "level", profile.getPlayerLevel());
        putIfPresent(context, "play_style", profile.getPlayStyle());
        putIfPresent(context, "kingdom", profile.getKingdom());
        JsonNode additional = profile.getAdditionalContext();
        if (additional != null && additional.isObject()) {
            context.putAll(objectMapper.convertValue(additional, PLAYER_CONTEXT_TYPE));
        }
        if (overrides != null) {
            context.putAll(overrides);
        }
        // Saved preferences take precedence over per-message overrides and JSON extras.
        context.remove("level");
        context.remove("play_style");
        context.remove("kingdom");
        putIfPresent(context, "level", profile.getPlayerLevel());
        putIfPresent(context, "play_style", profile.getPlayStyle());
        putIfPresent(context, "kingdom", profile.getKingdom());
        context.put("response_length", profile.getResponseLength());
        return context;
    }

    private void putIfPresent(Map<String, Object> target, String key, String value) {
        if (value != null && !value.isBlank()) {
            target.put(key, value);
        }
    }

    private ChatThreadDto toThreadDto(ChatThread thread, List<ChatMessageDto> messages) {
        return ChatThreadDto.builder()
                .id(thread.getId())
                .title(thread.getTitle())
                .language(thread.getLanguage())
                .gameVersion(thread.getGameVersion())
                .createdAt(thread.getCreatedAt())
                .updatedAt(thread.getUpdatedAt())
                .messages(messages == null ? new ArrayList<>() : messages)
                .build();
    }

    private ChatMessageDto toMessageDto(ChatMessage message) {
        return ChatMessageDto.builder()
                .id(message.getId())
                .role(message.getRole().name().toLowerCase())
                .content(message.getContent())
                .confidence(message.getConfidence() == null ? null : message.getConfidence().doubleValue())
                .sources(message.getSources())
                .intent(message.getIntent())
                .gameVersion(message.getGameVersion())
                .generationMode(message.getGenerationMode())
                .createdAt(message.getCreatedAt())
                .build();
    }

    private PlayerProfileDto toProfileDto(PlayerProfile profile) {
        return PlayerProfileDto.builder()
                .language(profile.getLanguage())
                .responseLength(profile.getResponseLength())
                .versionMode(profile.getVersionMode())
                .setupCompleted(profile.isSetupCompleted())
                .gameVersion(profile.getGameVersion())
                .playerLevel(profile.getPlayerLevel())
                .playStyle(profile.getPlayStyle())
                .kingdom(profile.getKingdom())
                .additionalContext(profile.getAdditionalContext())
                .build();
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
