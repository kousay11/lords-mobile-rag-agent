package com.project.backend.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.project.backend.clients.AgentClient;
import com.project.backend.dtos.LordsMobileChatRequestDto;
import com.project.backend.dtos.LordsMobileChatResponseDto;
import com.project.backend.entities.ChatMessage;
import com.project.backend.entities.ChatThread;
import com.project.backend.entities.PlayerProfile;
import com.project.backend.entities.User;
import com.project.backend.exceptions.ResourceNotFoundException;
import com.project.backend.repositories.AnswerFeedbackRepository;
import com.project.backend.repositories.ChatMessageRepository;
import com.project.backend.repositories.ChatThreadRepository;
import com.project.backend.repositories.PlayerProfileRepository;
import com.project.backend.services.implementations.ChatRateLimitService;
import com.project.backend.services.implementations.LordsMobileService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LordsMobileServiceTest {

    @Mock private ChatThreadRepository threadRepository;
    @Mock private ChatMessageRepository messageRepository;
    @Mock private AnswerFeedbackRepository feedbackRepository;
    @Mock private PlayerProfileRepository profileRepository;
    @Mock private AgentClient agentClient;
    @Mock private ChatRateLimitService rateLimitService;

    private LordsMobileService service;
    private User user;

    @BeforeEach
    void setUp() {
        service = new LordsMobileService(
                threadRepository,
                messageRepository,
                feedbackRepository,
                profileRepository,
                agentClient,
                rateLimitService,
                new ObjectMapper());
        user = User.builder().username("player").email("player@example.test").build();
        user.setId(UUID.randomUUID());
    }

    @Test
    void chatUsesAuthenticatedUserAndPersistsBothMessages() {
        UUID threadId = UUID.randomUUID();
        UUID assistantMessageId = UUID.randomUUID();
        PlayerProfile profile = PlayerProfile.builder()
                .user(user)
                .language("fr")
                .playStyle("free_to_play")
                .additionalContext(JsonNodeFactory.instance.objectNode())
                .build();
        when(profileRepository.findByUser(user)).thenReturn(Optional.of(profile));
        when(threadRepository.save(any(ChatThread.class))).thenAnswer(invocation -> {
            ChatThread thread = invocation.getArgument(0);
            if (thread.getId() == null) thread.setId(threadId);
            return thread;
        });
        when(messageRepository.save(any(ChatMessage.class))).thenAnswer(invocation -> {
            ChatMessage message = invocation.getArgument(0);
            if (message.getRole() == ChatMessage.Role.ASSISTANT) message.setId(assistantMessageId);
            return message;
        });
        when(agentClient.chat(any())).thenReturn(new AgentClient.AgentChatResponse(
                threadId.toString(),
                "Réponse documentée [1]",
                "model",
                "provider",
                "fact_lookup",
                "fr",
                "official-guide-2019-04-15",
                JsonNodeFactory.instance.arrayNode().addObject().put("title", "Guide officiel"),
                0.87,
                false,
                "hybrid",
                List.of("requête reformulée"),
                "safe_fallback",
                true));

        LordsMobileChatResponseDto response = service.chat(user, LordsMobileChatRequestDto.builder()
                .message("Comment fonctionne la chasse ?")
                .build());

        assertEquals(threadId, response.getThreadId());
        assertEquals(assistantMessageId, response.getMessageId());
        assertTrue(response.isReadOnly());
        assertEquals(0.87, response.getConfidence());

        ArgumentCaptor<AgentClient.AgentChatRequest> requestCaptor =
                ArgumentCaptor.forClass(AgentClient.AgentChatRequest.class);
        verify(agentClient).chat(requestCaptor.capture());
        assertEquals(user.getId().toString(), requestCaptor.getValue().userId());
        assertEquals("free_to_play", requestCaptor.getValue().playerContext().get("play_style"));
    }

    @Test
    void userCannotReadAnotherUsersThread() {
        UUID threadId = UUID.randomUUID();
        when(threadRepository.findByIdAndUser(threadId, user)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> service.getThread(user, threadId));
    }
}
