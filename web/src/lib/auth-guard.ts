import "server-only";

import { auth } from "@/auth";
import { isAllowedGitHubIdentity } from "@/lib/auth-policy";

export async function requireAuthorizedSession() {
  const session = await auth();
  if (
    !session?.user ||
    !isAllowedGitHubIdentity(session.user, process.env.NEXO_ALLOWED_GITHUB_ID)
  ) {
    throw new Error("Acesso não autorizado.");
  }
  return session;
}
