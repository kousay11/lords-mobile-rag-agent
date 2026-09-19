package com.project.backend.repositories;

import com.project.backend.entities.PlayerProfile;
import com.project.backend.entities.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface PlayerProfileRepository extends JpaRepository<PlayerProfile, UUID> {
    Optional<PlayerProfile> findByUser(User user);
}
