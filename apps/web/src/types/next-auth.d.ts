import { UserRole } from "./index";
import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id: string;
    role: UserRole;
    api_key: string;
    access_token?: string;
    refresh_token?: string;
    image?: string | null; 
  }

  interface Session {
    error?: "RefreshTokenExpired";
    user: {
      id: string;
      email: string;
      name: string;
      role: UserRole;
      image?: string | null; 
      api_key: string;
    };
  }
}

// declare module "next-auth/jwt" {
//   interface JWT {
//     id: string;
//     role: UserRole;
//     api_key: string;
//     access_token?: string;
//     refresh_token?: string;
//     expires_at?: number;
//     error?: "RefreshTokenExpired";
//     image?: string | null;
//   }
// }

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    role: UserRole;
    api_key: string;
    access_token?: string;
    refresh_token?: string;
    expires_at?: number;
    refresh_error_count?: number;
    error?: "RefreshTokenExpired";
    image?: string | null;
  }
}
