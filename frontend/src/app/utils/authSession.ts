const CURRENT_USER_EMAIL_KEY = "currentUserEmail";

export function getCurrentUserEmail() {
  return window.localStorage.getItem(CURRENT_USER_EMAIL_KEY) || "u001@careshot.local";
}

export function setCurrentUserEmail(userEmail: string) {
  window.localStorage.setItem(CURRENT_USER_EMAIL_KEY, userEmail);
}
