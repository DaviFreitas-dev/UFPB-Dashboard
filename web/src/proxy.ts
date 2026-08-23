export { auth as proxy } from "@/auth";

export const config = {
  matcher: [
    "/((?!api/auth|api/health|_next/static|_next/image|favicon.ico|entrar|acesso-negado).*)",
  ],
};
