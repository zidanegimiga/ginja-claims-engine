import NextAuth, { NextAuthConfig } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { createServerApiClient } from "./api-client";
import { AuthUser } from "@/types";

export const authConfig: NextAuthConfig = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },

      async authorize(credentials): Promise<AuthUser | null> {
        if (!credentials?.email || !credentials?.password) return null;

        // Development shortcut
        // Bypasses the API in local dev so the frontend can be built and
        // tested without a live auth backend. Remove before going to prod.
        if (process.env.NODE_ENV === "development") {
          if (
            credentials.email === process.env.DEV_USER_EMAIL &&
            credentials.password === process.env.DEV_USER_PASSWORD
          ) {
            return {
              id: "dev-001",
              email: credentials.email as string,
              name: "Zidane Gimiga",
              role: "admin",
              api_key: process.env.API_KEY_PRIMARY ?? "",
            };
          }
        }

        // Production path 
        try {
          const client = createServerApiClient();
          const { data } = await client.post<AuthUser>("/auth/login", {
            email: credentials.email,
            password: credentials.password,
          });
          return data;
        } catch {
          return null;
        }
      },
    }),
  ],

  session: {
    strategy: "jwt",
    maxAge: 8 * 60 * 60, // 8 hours
  },

  callbacks: {
    async jwt({ token, user }) {
      // Initial sign-in — attach user fields to the JWT
      if (user) {
        token.id = user.id;
        token.role = (user as AuthUser).role;
        token.api_key = (user as AuthUser).api_key;
      }
      return token;
    },

    async session({ session, token }) {
      session.user.id = token.id as string;
      session.user.role = token.role;
      session.user.api_key = token.api_key;
      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);