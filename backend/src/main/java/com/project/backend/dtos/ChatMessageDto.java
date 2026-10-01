package com.project.backend.dtos;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatMessageDto {
    private UUID id;
    private String role;
    private String content;
    private Double confidence;
    private JsonNode sources;
    private String intent;
    private String generationMode;
    private Instant createdAt;
}
