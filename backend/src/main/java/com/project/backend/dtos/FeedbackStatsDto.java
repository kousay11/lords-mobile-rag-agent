package com.project.backend.dtos;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Anonymous aggregate of answer feedback. Never exposes users, messages or comments.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FeedbackStatsDto {
    private long helpful;
    private long notHelpful;
    private long total;
    /** Share of helpful votes in [0,1], 0 when there are no votes. */
    private double helpfulRatio;
    private List<DayPoint> series;
    private List<IntentPoint> byIntent;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DayPoint {
        /** ISO date (yyyy-MM-dd) in UTC. */
        private String date;
        private long helpful;
        private long notHelpful;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IntentPoint {
        private String intent;
        private long helpful;
        private long notHelpful;
    }
}
