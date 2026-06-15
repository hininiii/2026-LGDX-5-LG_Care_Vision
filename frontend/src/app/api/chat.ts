import {
  AVAILABLE_DATES,
  initialMessages,
  PROBLEM_OPTIONS,
  PRODUCTS,
  PRODUCT_TYPES,
  TIME_SLOTS,
} from "../data/mockChat";
import { apiPost } from "./client";
import type { AiChatResponse, ChatContext, Message, ScheduleDateOption } from "../types/chat";

export function getInitialChatMessages(): Message[] {
  return initialMessages;
}

export function getProductCategories(): string[] {
  return PRODUCTS;
}

export function getProductTypes(productCategory: string): string[] {
  return PRODUCT_TYPES[productCategory] ?? [];
}

export function getAllProductTypes(): string[] {
  return Object.values(PRODUCT_TYPES).flat();
}

export function getProblemOptions(): string[] {
  return PROBLEM_OPTIONS;
}

export function getAvailableDates(): ScheduleDateOption[] {
  return AVAILABLE_DATES;
}

export function getTimeSlots(): string[] {
  return TIME_SLOTS;
}

export async function saveChatMessage(message: string, context: ChatContext): Promise<void> {
  await apiPost<{ saved: boolean }, { message: string; context: ChatContext }>(
    "/chat-messages",
    { message, context },
  );
}

export async function requestAiChat(message: string, context: ChatContext): Promise<AiChatResponse> {
  return apiPost<AiChatResponse, { message: string; context: ChatContext; include_rag_evidence: boolean }>(
    "/ai/chat",
    { message, context, include_rag_evidence: true },
  );
}

