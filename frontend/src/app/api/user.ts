import { apiGet, apiPost } from "./client";
import type { UserProfile } from "../types/user";
import { getCurrentUserEmail } from "../utils/authSession";
import { getUserProfile as getMockUserProfile } from "../data/mockUser";

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
  region_id?: string;
  region?: string;
  city?: string;
};

export type LoginUserPayload = {
  user_email: string;
  password: string;
};

type LocalUserRecord = UserProfile & {
  password?: string;
};

const LOCAL_USER_PROFILE_KEY = "careVisionUserProfile";
const LOCAL_USER_PROFILES_KEY = "careVisionUserProfiles";

function normalizeEmail(userEmail?: string) {
  return String(userEmail || "").trim().toLowerCase();
}

function getLocalProfiles(): Record<string, LocalUserRecord> {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_USER_PROFILES_KEY) || "{}");
  } catch {
    return {};
  }
}

function getLocalUserProfile(userEmail?: string): LocalUserRecord | null {
  const normalizedEmail = normalizeEmail(userEmail);
  const profiles = getLocalProfiles();
  if (normalizedEmail && profiles[normalizedEmail]) {
    return profiles[normalizedEmail];
  }

  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_USER_PROFILE_KEY) || "null");
  } catch {
    return null;
  }
}

function saveLocalUserProfile(payload: RegisterUserPayload): UserEnvelope {
  const normalizedEmail = normalizeEmail(payload.user_email);
  const profile: LocalUserRecord = {
    user_email: normalizedEmail,
    email: normalizedEmail,
    name: payload.name,
    phone: payload.phone,
    address: payload.address,
    password: payload.password,
    region_id: payload.region_id,
    region: payload.region,
    city: payload.city,
  };
  const profiles = getLocalProfiles();
  profiles[normalizedEmail] = profile;
  window.localStorage.setItem(LOCAL_USER_PROFILES_KEY, JSON.stringify(profiles));
  window.localStorage.setItem(LOCAL_USER_PROFILE_KEY, JSON.stringify(profile));
  return {
    user: profile,
  };
}

export async function getUserProfile(): Promise<UserProfile> {
  const params = new URLSearchParams({ user_email: getCurrentUserEmail() });
  try {
    return await apiGet<UserProfile>(`/users/me?${params.toString()}`);
  } catch {
    return getLocalUserProfile(getCurrentUserEmail()) ?? getMockUserProfile();
  }
}

export async function registerUser(payload: RegisterUserPayload): Promise<UserEnvelope> {
  const response = await apiPost<UserEnvelope, RegisterUserPayload>("/users/register", payload);
  saveLocalUserProfile(payload);
  return response;
}

export async function loginUser(payload: LoginUserPayload): Promise<UserEnvelope> {
  return apiPost<UserEnvelope, LoginUserPayload>("/users/login", payload);
}

export async function updateUserProfile(payload: RegisterUserPayload): Promise<UserEnvelope> {
  const response = await apiPost<UserEnvelope, RegisterUserPayload>("/users/me", payload, "PUT");
  saveLocalUserProfile(payload);
  return response;
}
