package com.project.backend.dtos;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LordsMobileChatResponseDto {
    private UUID threadId;
    private UUID messageId;
    private String response;
    private String intent;
    private String language;
    private JsonNode sources;
    private double confidence;
    private boolean needsClarification;
    private String searchType;
    private List<String> rewrittenQueries;
    private String generationMode;
    private boolean readOnly;
}
