package com.project.backend.entities;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "player_profiles")
public class PlayerProfile extends BaseEntity {

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;

    @Column(nullable = false, length = 16)
    private String language;

    @Column(name = "game_version", length = 50)
    private String gameVersion;

    @Column(name = "response_length", length = 16)
    private String responseLength;

    @Column(name = "version_mode", length = 16)
    private String versionMode;

    @Column(name = "setup_completed", nullable = false, columnDefinition = "boolean default false")
    private boolean setupCompleted;

    @Column(name = "player_level", length = 100)
    private String playerLevel;

    @Column(name = "play_style", length = 100)
    private String playStyle;

    @Column(length = 100)
    private String kingdom;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "additional_context", columnDefinition = "jsonb")
    private JsonNode additionalContext;
}
