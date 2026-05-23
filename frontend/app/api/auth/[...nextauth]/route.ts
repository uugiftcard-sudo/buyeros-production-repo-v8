import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const ADMIN_USERS = process.env.NEXTAUTH_USERS || "";
const ADMIN_HASH = process.env.NEXTAUTH_PASSWORD_HASH || "";

function verifyPassword(password: string): boolean {
  if (!ADMIN_USERS || !ADMIN_HASH) {
    // Dev mode: accept any non-empty credentials
    return password.length > 0;
  }
  const users = ADMIN_USERS.split(",").map((u) => u.trim());
  const hashes = ADMIN_HASH.split(",").map((h) => h.trim());
  return users.some((u, i) => u !== "" && hashes[i] === password);
}

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Admin",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const { username = "", password = "" } = credentials ?? {};
        if (!username || !verifyPassword(password)) return null;
        return { id: username, name: username, email: `${username}@buyeros.local` };
      },
    }),
  ],
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) token.role = "admin";
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as { role?: string }).role = token.role as string;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
