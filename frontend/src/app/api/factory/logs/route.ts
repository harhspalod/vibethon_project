import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  try {
    const FACTORY_URL = process.env.FACTORY_URL || "http://localhost:8001";
    const FACTORY_TOKEN = process.env.FACTORY_TOKEN || "bearer-token-2024";

    const response = await fetch(`${FACTORY_URL}/workflow/all-logs`, {
      headers: {
        Authorization: `Bearer ${FACTORY_TOKEN}`,
      },
      cache: "no-store",
    });

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error: any) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500 }
    );
  }
}