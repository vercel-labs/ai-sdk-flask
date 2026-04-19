import { checkBotId } from "botid/server";

export default async function middleware() {
  const verification = await checkBotId();

  if (verification.isBot) {
    return new Response(JSON.stringify({ error: "Access denied" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export const config = {
  matcher: ["/api/generate"],
};
