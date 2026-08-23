import NextAuth, { type NextAuthConfig } from "next-auth";
import GitHub from "next-auth/providers/github";

import { isAllowedGitHubIdentity } from "@/lib/auth-policy";

type GitHubProfile = {
  id?: number | string;
  login?: string;
};

export const authConfig = {
  providers: [GitHub],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/entrar",
    error: "/acesso-negado",
  },
  callbacks: {
    signIn({ account, profile }) {
      const github = profile as GitHubProfile | undefined;
      return isAllowedGitHubIdentity(
        {
          githubId: account?.providerAccountId ?? String(github?.id ?? ""),
          githubLogin: github?.login ?? "",
        },
        process.env.NEXO_ALLOWED_GITHUB_ID,
      );
    },
    jwt({ token, account, profile }) {
      if (account?.providerAccountId) {
        token.githubId = account.providerAccountId;
      }
      const github = profile as GitHubProfile | undefined;
      if (github?.login) {
        token.githubLogin = github.login;
      }
      return token;
    },
    session({ session, token }) {
      session.user.githubId =
        typeof token.githubId === "string" ? token.githubId : "";
      session.user.githubLogin =
        typeof token.githubLogin === "string" ? token.githubLogin : "";
      return session;
    },
    authorized({ auth: session }) {
      return isAllowedGitHubIdentity(
        session?.user,
        process.env.NEXO_ALLOWED_GITHUB_ID,
      );
    },
  },
} satisfies NextAuthConfig;

export const { auth, handlers, signIn, signOut } = NextAuth(authConfig);
