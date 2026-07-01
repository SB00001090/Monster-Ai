import { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";
import type { Express, Request, Response } from "express";
import type { User } from "../../drizzle/schema";
import * as db from "../db";
import { getSessionCookieOptions } from "./cookies";
import { ENV } from "./env";
import { memoryStore } from "./memoryStore";
import { sdk } from "./sdk";

const DEV_OPEN_ID = "dev_local_user";

function getQueryParam(req: Request, key: string): string | undefined {
  const value = req.query[key];
  return typeof value === "string" ? value : undefined;
}

export function registerOAuthRoutes(app: Express) {
  if (!ENV.isProduction) {
    app.get("/api/oauth/dev-login", async (req: Request, res: Response) => {
      const provider = getQueryParam(req, "provider");
      let openId = DEV_OPEN_ID;
      let loginMethod = "dev";
      let name = "Dev User";
      let email = "dev@monster-ai.local";

      if (provider === "google") {
        openId = "dev_google_user";
        loginMethod = "google";
        name = "Dev Google User";
        email = "dev-google@monster-ai.local";
      } else if (provider === "github") {
        openId = "dev_github_user";
        loginMethod = "github";
        name = "Dev GitHub User";
        email = "dev-github@monster-ai.local";
      }

      const devUser: User = {
        id: 1,
        openId,
        name,
        email,
        loginMethod,
        role: "user",
        llmConfig: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        lastSignedIn: new Date(),
      };

      memoryStore.upsertDevUser(devUser);
      if (process.env.DATABASE_URL) {
        await db.upsertUser({
          openId: devUser.openId,
          name: devUser.name,
          email: devUser.email,
          loginMethod: devUser.loginMethod,
          lastSignedIn: devUser.lastSignedIn,
        });
      }

      const sessionToken = await sdk.createSessionToken(devUser.openId, {
        name: devUser.name ?? "Dev User",
        expiresInMs: ONE_YEAR_MS,
      });

      const cookieOptions = getSessionCookieOptions(req);
      res.cookie(COOKIE_NAME, sessionToken, { ...cookieOptions, maxAge: ONE_YEAR_MS });
      res.redirect(302, "/");
    });
  }

  app.get("/api/oauth/callback", async (req: Request, res: Response) => {
    const code = getQueryParam(req, "code");
    const state = getQueryParam(req, "state");

    if (!code || !state) {
      res.status(400).json({ error: "code and state are required" });
      return;
    }

    try {
      const tokenResponse = await sdk.exchangeCodeForToken(code, state);
      const userInfo = await sdk.getUserInfo(tokenResponse.accessToken);

      if (!userInfo.openId) {
        res.status(400).json({ error: "openId missing from user info" });
        return;
      }

      await db.upsertUser({
        openId: userInfo.openId,
        name: userInfo.name || null,
        email: userInfo.email ?? null,
        loginMethod: userInfo.loginMethod ?? userInfo.platform ?? null,
        lastSignedIn: new Date(),
      });

      const sessionToken = await sdk.createSessionToken(userInfo.openId, {
        name: userInfo.name || "",
        expiresInMs: ONE_YEAR_MS,
      });

      const cookieOptions = getSessionCookieOptions(req);
      res.cookie(COOKIE_NAME, sessionToken, { ...cookieOptions, maxAge: ONE_YEAR_MS });

      res.redirect(302, "/");
    } catch (error) {
      console.error("[OAuth] Callback failed", error);
      res.status(500).json({ error: "OAuth callback failed" });
    }
  });
}
