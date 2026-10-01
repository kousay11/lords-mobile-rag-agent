package com.project.backend.services;

import com.project.backend.dtos.FeedbackStatsDto;
import com.project.backend.entities.AnswerFeedback;
import com.project.backend.entities.ChatMessage;
import com.project.backend.repositories.AnswerFeedbackRepository;
import com.project.backend.services.implementations.FeedbackStatsService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FeedbackStatsServiceTest {

    @Mock private AnswerFeedbackRepository repository;

    private static AnswerFeedback vote(AnswerFeedback.Rating rating, String intent, Instant createdAt)
            throws Exception {
        ChatMessage message = ChatMessage.builder()
                .role(ChatMessage.Role.ASSISTANT)
                .content("Réponse documentée [1]")
                .intent(intent)
                .build();
        AnswerFeedback feedback = AnswerFeedback.builder()
                .message(message)
                .rating(rating)
                .build();
        Field createdAtField = AnswerFeedback.class.getSuperclass().getDeclaredField("createdAt");
        createdAtField.setAccessible(true);
        createdAtField.set(feedback, createdAt);
        return feedback;
    }

    @Test
    void statsAreAnonymousAggregatesWithDailySeries() throws Exception {
        Instant now = Instant.now();
        when(repository.findByCreatedAtAfter(any(Instant.class))).thenReturn(List.of(
                vote(AnswerFeedback.Rating.HELPFUL, "fact_lookup", now),
                vote(AnswerFeedback.Rating.HELPFUL, "fact_lookup", now),
                vote(AnswerFeedback.Rating.NOT_HELPFUL, "how_to", now)));

        FeedbackStatsDto stats = new FeedbackStatsService(repository).stats(7);

        assertEquals(2, stats.getHelpful());
        assertEquals(1, stats.getNotHelpful());
        assertEquals(3, stats.getTotal());
        assertEquals(0.667, stats.getHelpfulRatio());
        assertEquals(7, stats.getSeries().size());
        assertEquals(3, stats.getSeries().get(6).getHelpful()
                + stats.getSeries().get(6).getNotHelpful());
        assertEquals(2, stats.getByIntent().size());
        assertEquals("fact_lookup", stats.getByIntent().get(0).getIntent());
    }

    @Test
    void emptyCorpusReturnsZeroedStats() {
        when(repository.findByCreatedAtAfter(any(Instant.class))).thenReturn(List.of());

        FeedbackStatsDto stats = new FeedbackStatsService(repository).stats(30);

        assertEquals(0, stats.getTotal());
        assertEquals(0.0, stats.getHelpfulRatio());
        assertEquals(30, stats.getSeries().size());
        assertTrue(stats.getByIntent().isEmpty());
    }
}
