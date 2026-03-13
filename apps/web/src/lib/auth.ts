import NextAuth, { NextAuthConfig } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import AzureADProvider from "next-auth/providers/azure-ad";
import axios from "axios";
import { AuthUser, UserRole } from "@/types";

const API = process.env.API_URL ?? "http://localhost:8000/api/v1";

// All OAuth providers whose sign-in should create/link a user in FastAPI
const OAUTH_PROVIDERS = ["google", "azure-ad"];

// Maps NextAuth provider id → value FastAPI expects
const PROVIDER_MAP: Record<string, string> = {
  google: "google",
  "azure-ad": "microsoft",
};

export const authConfig: NextAuthConfig = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),

    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      authorization: {
        url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        params: { scope: "openid profile email User.Read" },
      },
      token: "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    }),

    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        mode: { label: "Mode", type: "text" },
        name: { label: "Name", type: "text" },
      },

      async authorize(credentials): Promise<AuthUser | null> {
        if (!credentials?.email || !credentials?.password) return null;

        const endpoint =
          credentials.mode === "register" ? "/auth/register" : "/auth/login";

        const body =
          credentials.mode === "register"
            ? {
                email: credentials.email,
                password: credentials.password,
                full_name: credentials.name,
              }
            : {
                email: credentials.email,
                password: credentials.password,
              };

        try {
          const { data: tokens } = await axios.post(`${API}${endpoint}`, body);
          const { data: user } = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });

          return {
            id: user.id,
            email: user.email,
            name: user.full_name,
            role: user.role,
            api_key: process.env.API_KEY_PRIMARY ?? "",
            access_token: tokens.access_token,
            refresh_token: tokens.refresh_token,
          } as AuthUser;
        } catch {
          return null;
        }
      },
    }),
  ],

  session: { strategy: "jwt", maxAge: 7 * 24 * 60 * 60 },

  callbacks: {
    async signIn({ user, account, profile }) {
      console.log("[auth:signIn] provider:", account?.provider);
      console.log("[auth:signIn] account:", JSON.stringify(account, null, 2));
      console.log("[auth:signIn] user:", JSON.stringify(user, null, 2));
      console.log("[auth:signIn] profile:", JSON.stringify(profile, null, 2));
      if (!account) return true;

      // Handle all OAuth providers generically
      if (OAUTH_PROVIDERS.includes(account.provider)) {
        try {
          const provider = PROVIDER_MAP[account.provider];

          const { data: tokens } = await axios.post(`${API}/auth/oauth`, {
            email: user.email,
            full_name: user.name ?? user.email?.split("@")[0] ?? "Unknown",
            provider,
            provider_id: account.providerAccountId,
          });

          const { data: fapiUser } = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });

          // Attach to user object so jwt callback receives them
          user.role = fapiUser.role;
          user.api_key = process.env.API_KEY_PRIMARY ?? "";
          user.access_token = tokens.access_token;
          user.refresh_token = tokens.refresh_token;
        } catch (e) {
          console.error("[auth] OAuth FastAPI link failed:", e);
          return false;
        }
      }

      return true;
    },

    async jwt({ token, user }) {
      // Initial sign-in — user object is only present on first call
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.api_key = user.api_key;
        token.access_token = user.access_token;
        token.refresh_token = user.refresh_token;
        token.expires_at = Math.floor(Date.now() / 1000) + 15 * 60;
        token.refresh_error_count = 0;
        return token;
      }

      if (!token.expires_at) return token;

      const now = Math.floor(Date.now() / 1000);
      const expiresAt = token.expires_at as number;

      // Token still valid — nothing to do
      if (now < expiresAt - 180) return token;

      // No refresh token stored — session is unrecoverable
      if (!token.refresh_token) {
        return { ...token, error: "RefreshTokenExpired" };
      }

      // Silent refresh
      try {
        const { data } = await axios.post(`${API}/auth/refresh`, {
          refresh_token: token.refresh_token,
        });

        return {
          ...token,
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          expires_at: Math.floor(Date.now() / 1000) + 15 * 60,
          refresh_error_count: 0,
          error: undefined,
        };
      } catch {
        const errorCount = ((token.refresh_error_count as number) ?? 0) + 1;

        if (errorCount >= 2) {
          return {
            ...token,
            error: "RefreshTokenExpired",
            refresh_error_count: errorCount,
          };
        }

        return { ...token, refresh_error_count: errorCount };
      }
    },

    async session({ session, token }) {
      session.user.id = token.id as string;
      session.user.role = token.role as UserRole;
      session.user.api_key = token.api_key as string;
      session.error = token.error;
      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
