import NextAuth, { NextAuthConfig } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import axios from "axios";
import { AuthUser, UserRole } from "@/types";

const API = process.env.API_URL ?? "http://localhost:8000/api/v1";

export const authConfig: NextAuthConfig = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),

    MicrosoftEntraID({
      clientId: process.env.MICROSOFT_CLIENT_ID!,
      clientSecret: process.env.MICROSOFT_CLIENT_SECRET!,
      //   tenantId: process.env.MICROSOFT_TENANT_ID ?? "common",
    }),

    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        mode: { label: "Mode", type: "text" }, // "login" | "register"
        name: { label: "Name", type: "text" },
      },

      async authorize(credentials): Promise<AuthUser | null> {
        if (!credentials?.email || !credentials?.password) return null;

        // Dev shortcut
        if (process.env.NODE_ENV === "development") {
          if (
            credentials.email === process.env.DEV_USER_EMAIL &&
            credentials.password === process.env.DEV_USER_PASSWORD
          ) {
            return {
              id: "dev-001",
              email: credentials.email as string,
              name: "Zidane Gimiga",
              role: "admin" as UserRole,
              api_key: process.env.API_KEY_PRIMARY ?? "",
            };
          }
        }

        const endpoint =
          credentials.mode === "register" ? "/auth/register" : "/auth/login";

        const body =
          credentials.mode === "register"
            ? {
                email: credentials.email,
                password: credentials.password,
                full_name: credentials.name,
              }
            : { email: credentials.email, password: credentials.password };

        try {
          // Get token pair from FastAPI
          const { data: tokens } = await axios.post(`${API}${endpoint}`, body);

          // Fetch user profile
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
      // OAuth sign-in — create/link user in FastAPI
      if (
        account?.provider === "google" ||
        account?.provider === "microsoft-entra-id"
      ) {
        try {
          const provider =
            account.provider === "google" ? "google" : "microsoft";
          const { data: tokens } = await axios.post(`${API}/auth/oauth`, {
            email: user.email,
            full_name: user.name,
            provider,
            provider_id: account.providerAccountId,
          });

          const { data: fapiUser } = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${tokens.access_token}` },
          });

          // Attach to user object for jwt callback
          user.role = fapiUser.role;
          user.api_key = process.env.API_KEY_PRIMARY ?? "";
          user.access_token = tokens.access_token;
          user.refresh_token = tokens.refresh_token;
        } catch {
          return false; // Block sign in if FastAPI is unreachable
        }
      }
      return true;
    },

    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.api_key = user.api_key;
        token.access_token = user.access_token;
        token.refresh_token = user.refresh_token;
        token.expires_at = Math.floor(Date.now() / 1000) + 15 * 60;
      }

      // Silent refresh if access token expires in < 2 minutes, rotate
      const now = Math.floor(Date.now() / 1000);
      const expiresAt = (token.expires_at as number) ?? 0;

      if (now < expiresAt - 120) return token; // Still valid

      try {
        const { data } = await axios.post(`${API}/auth/refresh`, {
          refresh_token: token.refresh_token,
        });
        return {
          ...token,
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          expires_at: Math.floor(Date.now() / 1000) + 15 * 60,
        };
      } catch {
        // Refresh failed — force sign out on next request
        return { ...token, error: "RefreshTokenExpired" };
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
