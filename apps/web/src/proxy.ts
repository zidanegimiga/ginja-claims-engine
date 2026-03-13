import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_ROUTES = ["/login", "/api/auth"];

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isPublic = PUBLIC_ROUTES.some((r) => pathname.startsWith(r));

  if (isPublic) return NextResponse.next();

  if (!req.auth) {
    const url = new URL("/login", req.url);
    url.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(url);
  }

  if (req.auth?.error === "RefreshTokenExpired") {
    const url = new URL("/login", req.url);
    url.searchParams.set("error", "session_expired");
    return NextResponse.redirect(url);
  }

  const res = NextResponse.next();

  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  res.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  res.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: blob:",
      "connect-src 'self' http://localhost:8000 https://*.railway.app",
    ].join("; ")
  );

  return res;
});

// export async function proxy(req: NextRequest) {
//   const session = await auth();
//   const { pathname } = req.nextUrl;

//   const isLoggedIn  = !!session;
//   const isAuthPage  = pathname.startsWith("/login") || pathname.startsWith("/register");
//   const isDashboard = pathname.startsWith("/dashboard");

//   if (isDashboard && !isLoggedIn) {
//     return NextResponse.redirect(new URL("/login", req.url));
//   }

//   if (isAuthPage && isLoggedIn) {
//     return NextResponse.redirect(new URL("/dashboard", req.url));
//   }

//   return NextResponse.next();
// }

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|public).*)"],
};

