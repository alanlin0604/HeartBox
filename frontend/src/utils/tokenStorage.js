const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';
const REMEMBER_KEY = 'remember_me';

function readFrom(storage, key) {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function writeTo(storage, key, value) {
  try {
    storage.setItem(key, value);
  } catch {
    // Ignore unavailable storage in restrictive environments.
  }
}

function removeFrom(storage, key) {
  try {
    storage.removeItem(key);
  } catch {
    // Ignore unavailable storage in restrictive environments.
  }
}

export function isRememberedLogin() {
  return readFrom(localStorage, REMEMBER_KEY) === '1';
}

export function setAuthTokens(access, refresh, rememberMe) {
  const persistent = Boolean(rememberMe);
  writeTo(localStorage, REMEMBER_KEY, persistent ? '1' : '0');

  const primary = persistent ? localStorage : sessionStorage;
  const secondary = persistent ? sessionStorage : localStorage;

  writeTo(primary, ACCESS_KEY, access);
  writeTo(primary, REFRESH_KEY, refresh);
  removeFrom(secondary, ACCESS_KEY);
  removeFrom(secondary, REFRESH_KEY);
}

export function getAccessToken() {
  return readFrom(localStorage, ACCESS_KEY) || readFrom(sessionStorage, ACCESS_KEY);
}

export function getRefreshToken() {
  return readFrom(localStorage, REFRESH_KEY) || readFrom(sessionStorage, REFRESH_KEY);
}

export function setAccessToken(access) {
  if (readFrom(localStorage, ACCESS_KEY)) {
    writeTo(localStorage, ACCESS_KEY, access);
    return;
  }
  writeTo(sessionStorage, ACCESS_KEY, access);
}

export function setRefreshToken(refresh) {
  if (readFrom(localStorage, REFRESH_KEY)) {
    writeTo(localStorage, REFRESH_KEY, refresh);
    return;
  }
  writeTo(sessionStorage, REFRESH_KEY, refresh);
}

export function clearAuthTokens() {
  removeFrom(localStorage, ACCESS_KEY);
  removeFrom(localStorage, REFRESH_KEY);
  removeFrom(sessionStorage, ACCESS_KEY);
  removeFrom(sessionStorage, REFRESH_KEY);
  removeFrom(localStorage, REMEMBER_KEY);
}
