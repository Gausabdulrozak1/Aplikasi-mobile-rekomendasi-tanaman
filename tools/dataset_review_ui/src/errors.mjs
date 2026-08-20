export class ReviewUiError extends Error {
  constructor(message, statusCode = 400, code = "REVIEW_UI_ERROR", details = undefined) {
    super(message);
    this.name = "ReviewUiError";
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export class ValidationError extends ReviewUiError {
  constructor(message, code = "VALIDATION_ERROR", details = undefined) {
    super(message, 422, code, details);
    this.name = "ValidationError";
  }
}

export class ConflictError extends ReviewUiError {
  constructor(message, code = "CONFLICT", details = undefined) {
    super(message, 409, code, details);
    this.name = "ConflictError";
  }
}
