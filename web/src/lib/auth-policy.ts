export type GitHubIdentity = {
  githubId?: string | null;
  githubLogin?: string | null;
};

export function isAllowedGitHubIdentity(
  identity: GitHubIdentity | null | undefined,
  allowedId: string | undefined,
): boolean {
  const expected = allowedId?.trim();
  return Boolean(
    expected && /^\d+$/.test(expected) && identity?.githubId === expected,
  );
}
