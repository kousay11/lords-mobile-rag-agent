package com.project.backend.config;

import com.project.backend.entities.User;
import com.project.backend.repositories.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "app.bootstrap-admin", name = "enabled", havingValue = "true")
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${app.bootstrap-admin.username}")
    private String username;

    @Value("${app.bootstrap-admin.email}")
    private String email;

    @Value("${app.bootstrap-admin.password}")
    private String password;

    @Override
    public void run(String... args) {
        if (password == null || password.isBlank()) {
            throw new IllegalStateException(
                    "BOOTSTRAP_ADMIN_PASSWORD is required when bootstrap admin is enabled");
        }
        if (userRepository.findByUsername(username).isEmpty()) {
            User admin = User.builder()
                    .username(username)
                    .email(email)
                    .password(passwordEncoder.encode(password))
                    .role(User.Role.ADMIN)
                    .profileRole(User.ProfileRole.PLAYER)
                    .build();
            userRepository.save(admin);
            log.info("Bootstrap administrator created: {}", username);
        }
    }
}
