package com.project.backend.dtos;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Paginated NOT_HELPFUL feedback items for corpus enrichment. No user data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NegativeFeedbackPageDto {
    private List<NegativeFeedbackDto> items;
    private long total;
    private int page;
    private int size;
}
