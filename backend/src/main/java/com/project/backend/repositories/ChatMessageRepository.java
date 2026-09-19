package com.project.backend.repositories;

import com.project.backend.entities.ChatMessage;
import com.project.backend.entities.ChatThread;
import com.project.backend.entities.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, UUID> {
    List<ChatMessage> findAllByThreadOrderByCreatedAtAsc(ChatThread thread);

    void deleteAllByThread(ChatThread thread);

    Optional<ChatMessage> findByIdAndThreadUser(UUID id, User user);
}
