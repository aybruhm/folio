export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}

export interface ErrorResponse {
  status: number;
  message: string;
  errors?: ValidationError[];
}
