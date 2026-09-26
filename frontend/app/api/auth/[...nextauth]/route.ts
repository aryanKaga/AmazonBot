import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text", placeholder: "demo" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Demo credentials — swap for a real DB lookup later
        if (
          credentials?.username === "demo" &&
          credentials?.password === "password"
        ) {
          return { id: "1", name: "Demo User", email: "demo@amazon-bot.dev" };
        }
        return null;
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) token.id = user.id;
      return token;
    },
    async session({ session, token }) {
      if (session.user) session.user.id = token.id as string;
      return session;
    },
  },
});

export { handler as GET, handler as POST };
