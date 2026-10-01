package com.project.backend.repositories;

import com.project.backend.entities.AnswerFeedback;
import com.project.backend.entities.ChatMessage;
import com.project.backend.entities.User;
import com.project.backend.entities.ChatThread;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface AnswerFeedbackRepository extends JpaRepository<AnswerFeedback, UUID> {
    Optional<AnswerFeedback> findByMessageAndUser(ChatMessage message, User user);

    List<AnswerFeedback> findByCreatedAtAfter(Instant since);

    void deleteAllByMessageThread(ChatThread thread);
}
