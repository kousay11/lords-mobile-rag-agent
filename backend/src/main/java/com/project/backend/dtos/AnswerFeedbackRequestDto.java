package com.project.backend.dtos;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnswerFeedbackRequestDto {

    @NotBlank
    @Pattern(regexp = "^(HELPFUL|NOT_HELPFUL)$")
    private String rating;

    @Size(max = 2000)
    private String comment;
}
