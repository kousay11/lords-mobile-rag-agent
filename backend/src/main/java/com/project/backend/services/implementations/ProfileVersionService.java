package com.project.backend.services.implementations;

import com.project.backend.clients.RagClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;

@Service
@RequiredArgsConstructor
public class ProfileVersionService {
    private final RagClient ragClient;

    public record VersionOption(String value, String label, String kind, int documentCount,
                                int needsReviewCount, int archivedCount) {}

    // Enumerate indexed metadata, not just numeric releases. Never infer a release from a year.
    public List<VersionOption> versionOptions() {
        var counts = new TreeMap<String, int[]>();
        JsonNode documents = ragClient.listDocuments();
        for (JsonNode doc : documents.path("data")) {
            String version = doc.path("game_version").asText("").trim();
            if (version.isEmpty() || version.length() > 50) continue;
            int[] count = counts.computeIfAbsent(version, key -> new int[3]);
            count[0]++;
            if (doc.path("status").asText().equals("needs_review")) count[1]++;
            if (doc.path("status").asText().equals("deprecated")) count[2]++;
        }
        var result = new ArrayList<VersionOption>();
        counts.forEach((value, count) -> {
            String kind = "corpus";
            String label = "Corpus " + value;
            if (value.matches("\\d{4}-review")) {
                kind = "review";
                label = "Corpus " + value.substring(0, 4) + " — sources avec réserves";
            } else if (value.startsWith("official-guide-")) {
                kind = "guide";
                label = "Guides officiels — " + value.substring("official-guide-".length());
            } else if (value.matches("\\d+(?:\\.\\d+){1,2}")) {
                kind = "release";
                label = "Version " + value + (count[2] == count[0] ? " — archive" : "");
            }
            result.add(new VersionOption(value, label, kind, count[0], count[1], count[2]));
        });
        return result;
    }

    public List<String> supportedVersions() {
        return versionOptions().stream().map(VersionOption::value).toList();
    }
}
