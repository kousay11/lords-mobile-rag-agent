package com.project.backend.repositories;

import com.project.backend.entities.ChatThread;
import com.project.backend.entities.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ChatThreadRepository extends JpaRepository<ChatThread, UUID> {
    List<ChatThread> findAllByUserOrderByUpdatedAtDesc(User user);

    Optional<ChatThread> findByIdAndUser(UUID id, User user);
}
