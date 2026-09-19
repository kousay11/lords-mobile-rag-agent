package com.project.backend.exceptions;

import org.springframework.http.HttpStatus;

public class DownstreamServiceException extends RuntimeException {

    private final HttpStatus status;

    public DownstreamServiceException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }
}
