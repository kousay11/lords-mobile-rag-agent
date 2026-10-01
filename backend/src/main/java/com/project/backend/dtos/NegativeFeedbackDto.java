package com.project.backend.dtos;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * One NOT_HELPFUL vote with its question context. Never exposes user data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NegativeFeedbackDto {
    private UUID feedbackId;
    private Instant createdAt;
    private String intent;
    private BigDecimal confidence;
    private String question;
    private String answerExcerpt;
    private String comment;
    private UUID threadId;
    private UUID messageId;
    private JsonNode sources;
}
