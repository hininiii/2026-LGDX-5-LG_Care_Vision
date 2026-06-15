import { apiGet, apiPost } from "./client";
import type { UserProfile } from "../types/user";
import { getCurrentUserEmail } from "../utils/authSession";

type UserEnvelope = {
  user: UserProfile;
  demo_seed?: Record<string, unknown>;
};

export type RegisterUserPayload = {
  user_email: string;
  password?: string;
  name: string;
  phone: string;
  address: string;
  preferred_language?: string;
};

export type LoginUserPayload = {
  user_email: string;
  password: string;
};

export async function getUserProfile(): Promise<UserProfile> {
  const params = new URLSearchParams({ user_email: getCurrentUserEmail() });
  return apiGet<UserProfile>(`/users/me?${params.toString()}`);
}

export async function registerUser(payload: RegisterUserPayload): Promise<UserEnvelope> {
  return apiPost<UserEnvelope, RegisterUserPayload>("/users/register", payload);
}

export async function loginUser(payload: LoginUserPayload): Promise<UserEnvelope> {
  return apiPost<UserEnvelope, LoginUserPayload>("/users/login", payload);
}

export async function updateUserProfile(payload: RegisterUserPayload): Promise<UserEnvelope> {
  return apiPost<UserEnvelope, RegisterUserPayload>("/users/me", payload, "PUT");
}
