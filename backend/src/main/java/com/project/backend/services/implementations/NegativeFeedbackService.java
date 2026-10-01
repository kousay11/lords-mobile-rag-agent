package com.project.backend.services.implementations;

import com.project.backend.dtos.NegativeFeedbackDto;
import com.project.backend.dtos.NegativeFeedbackPageDto;
import com.project.backend.entities.AnswerFeedback;
import com.project.backend.entities.ChatMessage;
import com.project.backend.entities.ChatThread;
import com.project.backend.repositories.AnswerFeedbackRepository;
import com.project.backend.repositories.ChatMessageRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Lists NOT_HELPFUL votes with their question context for corpus enrichment.
 * Never exposes user data: no username, user id or thread ownership.
 */
@Service
@RequiredArgsConstructor
public class NegativeFeedbackService {

    private static final int MAX_ANSWER_EXCERPT = 1200;

    private final AnswerFeedbackRepository feedbackRepository;
    private final ChatMessageRepository messageRepository;

    @Transactional(readOnly = true)
    public NegativeFeedbackPageDto list(int days, String intent, String query, int page, int size) {
        int window = Math.max(1, Math.min(days, 90));
        int safeSize = Math.max(1, Math.min(size, 100));
        int safePage = Math.max(0, page);
        Instant since = Instant.now().minus(window, ChronoUnit.DAYS).truncatedTo(ChronoUnit.DAYS);

        String intentFilter = intent == null || intent.isBlank() ? null : intent.trim();
        String queryFilter = query == null || query.isBlank() ? null : query.trim().toLowerCase();

        List<NegativeFeedbackDto> all = new ArrayList<>();
        for (AnswerFeedback vote : feedbackRepository.findByCreatedAtAfter(since)) {
            if (vote.getRating() != AnswerFeedback.Rating.NOT_HELPFUL) {
                continue;
            }
            ChatMessage answer = vote.getMessage();
            if (answer == null) {
                continue;
            }
            String voteIntent = intentOf(answer);
            if (intentFilter != null && !intentFilter.equals(voteIntent)) {
                continue;
            }
            String question = previousUserMessage(answer);
            String answerText = answer.getContent() == null ? "" : answer.getContent();
            if (queryFilter != null && !matches(queryFilter, question, answerText, vote.getComment())) {
                continue;
            }
            all.add(NegativeFeedbackDto.builder()
                    .feedbackId(vote.getId())
                    .createdAt(vote.getCreatedAt())
                    .intent(voteIntent)
                    .confidence(answer.getConfidence())
                    .question(question)
                    .answerExcerpt(excerpt(answerText))
                    .comment(vote.getComment())
                    .threadId(threadIdOf(answer))
                    .messageId(answer.getId())
                    .sources(answer.getSources())
                    .build());
        }
        all.sort(Comparator.comparing(NegativeFeedbackDto::getCreatedAt,
                Comparator.nullsLast(Comparator.naturalOrder())).reversed());

        long total = all.size();
        int from = Math.min(safePage * safeSize, all.size());
        int to = Math.min(from + safeSize, all.size());
        return NegativeFeedbackPageDto.builder()
                .items(all.subList(from, to))
                .total(total)
                .page(safePage)
                .size(safeSize)
                .build();
    }

    private static String intentOf(ChatMessage answer) {
        if (answer.getIntent() != null && !answer.getIntent().isBlank()) {
            return answer.getIntent();
        }
        return "unknown";
    }

    private String previousUserMessage(ChatMessage answer) {
        try {
            ChatThread thread = answer.getThread();
            if (thread == null) {
                return "";
            }
            List<ChatMessage> messages = messageRepository.findAllByThreadOrderByCreatedAtAsc(thread);
            int answerIndex = -1;
            for (int i = 0; i < messages.size(); i++) {
                if (messages.get(i).getId() != null && messages.get(i).getId().equals(answer.getId())) {
                    answerIndex = i;
                    break;
                }
            }
            for (int i = answerIndex < 0 ? messages.size() - 1 : answerIndex - 1; i >= 0; i--) {
                ChatMessage candidate = messages.get(i);
                if (candidate.getRole() == ChatMessage.Role.USER
                        && candidate.getContent() != null && !candidate.getContent().isBlank()) {
                    return candidate.getContent();
                }
            }
        } catch (Exception ignored) {
        }
        return "";
    }

    private static java.util.UUID threadIdOf(ChatMessage answer) {
        try {
            return answer.getThread() == null ? null : answer.getThread().getId();
        } catch (Exception ex) {
            return null;
        }
    }

    private static boolean matches(String queryFilter, String question, String answer, String comment) {
        return contains(queryFilter, question)
                || contains(queryFilter, answer)
                || contains(queryFilter, comment);
    }

    private static boolean contains(String queryFilter, String value) {
        return value != null && value.toLowerCase().contains(queryFilter);
    }

    private static String excerpt(String value) {
        if (value == null) {
            return "";
        }
        if (value.length() <= MAX_ANSWER_EXCERPT) {
            return value;
        }
        return value.substring(0, MAX_ANSWER_EXCERPT) + "…";
    }
}
