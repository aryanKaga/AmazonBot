import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import ChatPage from "@/components/ChatPage";

export default async function Home() {
  const session = await getServerSession();
  if (!session) redirect("/login");
  return <ChatPage user={session.user} />;
}
