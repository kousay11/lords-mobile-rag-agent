package com.project.backend.dtos;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatThreadDto {
    private UUID id;
    private String title;
    private String language;
    private String gameVersion;
    private Instant createdAt;
    private Instant updatedAt;
    private List<ChatMessageDto> messages;
}
