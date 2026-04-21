import { randomUUID, randomBytes, createHash } from "crypto";
import type { Response } from "express";
import type {
  OAuthServerProvider,
  AuthorizationParams,
} from "@modelcontextprotocol/sdk/server/auth/provider.js";
import type { OAuthRegisteredClientsStore } from "@modelcontextprotocol/sdk/server/auth/clients.js";
import type {
  OAuthClientInformationFull,
  OAuthTokens,
  OAuthTokenRevocationRequest,
} from "@modelcontextprotocol/sdk/shared/auth.js";
import type { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";

const SERVER_PASSWORD = process.env.BEARER_TOKEN ?? "daylily";

// In-memory stores — fine for a single-instance server
const clients = new Map<string, OAuthClientInformationFull>();
const authCodes = new Map<
  string,
  {
    clientId: string;
    codeChallenge: string;
    redirectUri: string;
    expiresAt: number;
  }
>();
const accessTokens = new Map<
  string,
  { clientId: string; expiresAt: number }
>();
const refreshTokens = new Map<string, { clientId: string }>();

const clientsStore: OAuthRegisteredClientsStore = {
  async getClient(clientId: string) {
    let client = clients.get(clientId);
    if (!client) {
      // Auto-accept unknown client_ids — handles stale cached clients after
      // server restart. Safe for a single-user, password-protected server.
      console.error(`[OAuth] getClient(${clientId}) → auto-registering unknown client`);
      client = {
        client_id: clientId,
        client_name: "auto-registered",
        redirect_uris: [],
        grant_types: ["authorization_code", "refresh_token"],
        response_types: ["code"],
        token_endpoint_auth_method: "none",
      } as OAuthClientInformationFull;
      clients.set(clientId, client);
    }
    return client;
  },
  async registerClient(client: OAuthClientInformationFull) {
    clients.set(client.client_id, client);
    console.error(`[OAuth] registerClient(${client.client_id})`);
    return client;
  },
};

export const oauthProvider: OAuthServerProvider = {
  get clientsStore() {
    return clientsStore;
  },

  async authorize(
    client: OAuthClientInformationFull,
    params: AuthorizationParams,
    res: Response
  ) {
    // For a single-user server, auto-approve — the password was already
    // validated via the login form. Generate auth code and redirect.
    const code = randomUUID();
    authCodes.set(code, {
      clientId: client.client_id,
      codeChallenge: params.codeChallenge,
      redirectUri: params.redirectUri,
      expiresAt: Date.now() + 5 * 60 * 1000, // 5 min
    });

    const redirectUrl = new URL(params.redirectUri);
    redirectUrl.searchParams.set("code", code);
    if (params.state) {
      redirectUrl.searchParams.set("state", params.state);
    }
    res.redirect(302, redirectUrl.toString());
  },

  async challengeForAuthorizationCode(
    _client: OAuthClientInformationFull,
    authorizationCode: string
  ) {
    const entry = authCodes.get(authorizationCode);
    if (!entry || entry.expiresAt < Date.now()) {
      throw new Error("Invalid or expired authorization code");
    }
    return entry.codeChallenge;
  },

  async exchangeAuthorizationCode(
    client: OAuthClientInformationFull,
    authorizationCode: string
  ) {
    const entry = authCodes.get(authorizationCode);
    if (!entry || entry.expiresAt < Date.now()) {
      throw new Error("Invalid or expired authorization code");
    }
    if (entry.clientId !== client.client_id) {
      throw new Error("Client mismatch");
    }

    authCodes.delete(authorizationCode);

    const accessToken = randomBytes(32).toString("hex");
    const refreshToken = randomBytes(32).toString("hex");

    accessTokens.set(accessToken, {
      clientId: client.client_id,
      expiresAt: Date.now() + 3600 * 1000, // 1 hour
    });
    refreshTokens.set(refreshToken, { clientId: client.client_id });

    return {
      access_token: accessToken,
      token_type: "bearer",
      expires_in: 3600,
      refresh_token: refreshToken,
    } as OAuthTokens;
  },

  async exchangeRefreshToken(
    client: OAuthClientInformationFull,
    refreshToken: string
  ) {
    const entry = refreshTokens.get(refreshToken);
    if (!entry || entry.clientId !== client.client_id) {
      throw new Error("Invalid refresh token");
    }

    // Rotate tokens
    refreshTokens.delete(refreshToken);
    const newAccessToken = randomBytes(32).toString("hex");
    const newRefreshToken = randomBytes(32).toString("hex");

    accessTokens.set(newAccessToken, {
      clientId: client.client_id,
      expiresAt: Date.now() + 3600 * 1000,
    });
    refreshTokens.set(newRefreshToken, { clientId: client.client_id });

    return {
      access_token: newAccessToken,
      token_type: "bearer",
      expires_in: 3600,
      refresh_token: newRefreshToken,
    } as OAuthTokens;
  },

  async verifyAccessToken(token: string): Promise<AuthInfo> {
    const entry = accessTokens.get(token);
    if (!entry || entry.expiresAt < Date.now()) {
      throw new Error("Invalid or expired access token");
    }
    return {
      token,
      clientId: entry.clientId,
      scopes: [],
      expiresAt: Math.floor(entry.expiresAt / 1000),
    };
  },

  async revokeToken(
    _client: OAuthClientInformationFull,
    request: OAuthTokenRevocationRequest
  ) {
    accessTokens.delete(request.token);
    refreshTokens.delete(request.token);
  },
};
