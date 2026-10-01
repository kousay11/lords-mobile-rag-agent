package com.project.backend.controllers;

import com.project.backend.dtos.FeedbackStatsDto;
import com.project.backend.dtos.NegativeFeedbackPageDto;
import com.project.backend.dtos.UpdateRoleDto;
import com.project.backend.dtos.UserDto;
import com.project.backend.services.implementations.FeedbackStatsService;
import com.project.backend.services.implementations.NegativeFeedbackService;
import com.project.backend.services.interfaces.AdminService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class AdminController {

    private final AdminService adminService;
    private final FeedbackStatsService feedbackStatsService;
    private final NegativeFeedbackService negativeFeedbackService;

    @GetMapping("/users")
    public ResponseEntity<List<UserDto>> getAllUsers() {
        return ResponseEntity.ok(adminService.getAllUsers());
    }

    @PutMapping("/users/{id}/role")
    public ResponseEntity<UserDto> updateRole(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateRoleDto dto) {
        return ResponseEntity.ok(adminService.updateRole(id, dto.getRole()));
    }

    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable UUID id) {
        adminService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/feedback/stats")
    public ResponseEntity<FeedbackStatsDto> feedbackStats(
            @RequestParam(defaultValue = "30") int days) {
        return ResponseEntity.ok(feedbackStatsService.stats(days));
    }

    @GetMapping("/feedback/negative")
    public ResponseEntity<NegativeFeedbackPageDto> negativeFeedback(
            @RequestParam(defaultValue = "30") int days,
            @RequestParam(required = false) String intent,
            @RequestParam(required = false, name = "q") String query,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(negativeFeedbackService.list(days, intent, query, page, size));
    }
}
