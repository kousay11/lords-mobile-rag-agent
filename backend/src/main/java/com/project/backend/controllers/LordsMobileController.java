package com.project.backend.controllers;

import com.project.backend.dtos.AnswerFeedbackRequestDto;
import com.project.backend.dtos.ChatThreadDto;
import com.project.backend.dtos.LordsMobileChatRequestDto;
import com.project.backend.dtos.LordsMobileChatResponseDto;
import com.project.backend.dtos.PlayerProfileDto;
import com.project.backend.entities.User;
import com.project.backend.services.implementations.LordsMobileService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/lords-mobile")
@RequiredArgsConstructor
public class LordsMobileController {

    private final LordsMobileService service;

    @PostMapping("/chat")
    public ResponseEntity<LordsMobileChatResponseDto> chat(
            @AuthenticationPrincipal User user,
            @Valid @RequestBody LordsMobileChatRequestDto request) {
        return ResponseEntity.ok(service.chat(user, request));
    }

    @GetMapping("/threads")
    public ResponseEntity<List<ChatThreadDto>> listThreads(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(service.listThreads(user));
    }

    @GetMapping("/threads/{threadId}")
    public ResponseEntity<ChatThreadDto> getThread(
            @AuthenticationPrincipal User user,
            @PathVariable UUID threadId) {
        return ResponseEntity.ok(service.getThread(user, threadId));
    }

    @DeleteMapping("/threads/{threadId}")
    public ResponseEntity<Void> deleteThread(
            @AuthenticationPrincipal User user,
            @PathVariable UUID threadId) {
        service.deleteThread(user, threadId);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/messages/{messageId}/feedback")
    public ResponseEntity<Void> feedback(
            @AuthenticationPrincipal User user,
            @PathVariable UUID messageId,
            @Valid @RequestBody AnswerFeedbackRequestDto request) {
        service.saveFeedback(user, messageId, request);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/profile")
    public ResponseEntity<PlayerProfileDto> getProfile(@AuthenticationPrincipal User user) {
        return ResponseEntity.ok(service.getProfile(user));
    }

    @PutMapping("/profile")
    public ResponseEntity<PlayerProfileDto> updateProfile(
            @AuthenticationPrincipal User user,
            @Valid @RequestBody PlayerProfileDto request) {
        return ResponseEntity.ok(service.updateProfile(user, request));
    }
}
