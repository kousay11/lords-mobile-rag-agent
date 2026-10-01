package com.project.backend.services.implementations;

import com.project.backend.dtos.FeedbackStatsDto;
import com.project.backend.entities.AnswerFeedback;
import com.project.backend.repositories.AnswerFeedbackRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Anonymous feedback aggregates for the admin dashboard.
 * Only counts and ratios leave this service: no user, message or comment data.
 */
@Service
@RequiredArgsConstructor
public class FeedbackStatsService {

    private final AnswerFeedbackRepository repository;

    @Transactional(readOnly = true)
    public FeedbackStatsDto stats(int days) {
        int window = Math.max(1, Math.min(days, 90));
        Instant since = Instant.now().minus(window, ChronoUnit.DAYS).truncatedTo(ChronoUnit.DAYS);
        List<AnswerFeedback> votes = repository.findByCreatedAtAfter(since);

        long helpful = votes.stream()
                .filter(vote -> vote.getRating() == AnswerFeedback.Rating.HELPFUL)
                .count();
        long notHelpful = votes.size() - helpful;
        double ratio = votes.isEmpty() ? 0.0 : (double) helpful / votes.size();

        LocalDate today = LocalDate.now(ZoneOffset.UTC);
        Map<LocalDate, long[]> perDay = new LinkedHashMap<>();
        for (int i = window - 1; i >= 0; i--) {
            perDay.put(today.minusDays(i), new long[2]);
        }
        for (AnswerFeedback vote : votes) {
            if (vote.getCreatedAt() == null) {
                continue;
            }
            LocalDate day = vote.getCreatedAt().atZone(ZoneOffset.UTC).toLocalDate();
            long[] counts = perDay.get(day);
            if (counts == null) {
                continue;
            }
            if (vote.getRating() == AnswerFeedback.Rating.HELPFUL) {
                counts[0]++;
            } else {
                counts[1]++;
            }
        }
        List<FeedbackStatsDto.DayPoint> series = new ArrayList<>();
        perDay.forEach((day, counts) -> series.add(FeedbackStatsDto.DayPoint.builder()
                .date(day.toString())
                .helpful(counts[0])
                .notHelpful(counts[1])
                .build()));

        Map<String, long[]> perIntent = new LinkedHashMap<>();
        for (AnswerFeedback vote : votes) {
            String intent = "unknown";
            if (vote.getMessage() != null && vote.getMessage().getIntent() != null
                    && !vote.getMessage().getIntent().isBlank()) {
                intent = vote.getMessage().getIntent();
            }
            long[] counts = perIntent.computeIfAbsent(intent, key -> new long[2]);
            if (vote.getRating() == AnswerFeedback.Rating.HELPFUL) {
                counts[0]++;
            } else {
                counts[1]++;
            }
        }
        List<FeedbackStatsDto.IntentPoint> byIntent = perIntent.entrySet().stream()
                .map(entry -> FeedbackStatsDto.IntentPoint.builder()
                        .intent(entry.getKey())
                        .helpful(entry.getValue()[0])
                        .notHelpful(entry.getValue()[1])
                        .build())
                .sorted(Comparator.comparingLong(
                        (FeedbackStatsDto.IntentPoint point) -> point.getHelpful() + point.getNotHelpful())
                        .reversed())
                .toList();

        return FeedbackStatsDto.builder()
                .helpful(helpful)
                .notHelpful(notHelpful)
                .total(votes.size())
                .helpfulRatio(Math.round(ratio * 1000.0) / 1000.0)
                .series(series)
                .byIntent(byIntent)
                .build();
    }
}
