
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");

  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // Cookie updates may be handled by middleware.
          }
        },
      },
    }
  );

  if (!code) {
    return NextResponse.redirect(
      new URL("/verbly-ai/login?error=auth", request.url)
    );
  }

  const { data, error } =
    await supabase.auth.exchangeCodeForSession(code);

  if (error || !data.user) {
    console.error("Auth callback error:", error?.message);

    return NextResponse.redirect(
      new URL("/verbly-ai/login?error=auth", request.url)
    );
  }

  const user = data.user;

  // Only send a welcome email for recently created accounts.
  const createdAt = user.created_at
    ? new Date(user.created_at).getTime()
    : 0;

  const accountAge = Date.now() - createdAt;
  const isNewAccount =
    accountAge >= 0 && accountAge < 10 * 60 * 1000;

  if (isNewAccount && user.email) {
    try {
      const resendKey = process.env.RESEND_API_KEY;
      const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;

      if (!resendKey || !serviceKey || !supabaseUrl) {
        throw new Error("Welcome email environment variables are missing.");
      }

      const admin = createClient(supabaseUrl, serviceKey, {
        auth: {
          autoRefreshToken: false,
          persistSession: false,
        },
      });

      // The primary key prevents duplicate welcome emails.
      const { error: logError } = await admin
        .from("welcome_email_logs")
        .insert({ user_id: user.id });

      if (logError?.code === "23505") {
        console.log("Welcome email already processed for:", user.id);
      } else if (logError) {
        throw logError;
      } else {
        const resend = new Resend(resendKey);

        const name =
          user.user_metadata?.full_name ||
          user.user_metadata?.name ||
          "there";

        const safeName = escapeHtml(String(name));

        const { error: emailError } = await resend.emails.send({
          from: "Verbly AI <onboarding@resend.dev>",
          to: user.email,
          subject: "Welcome to Verbly AI! 🎉",
          html: `
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:30px;color:#222;">
              <h1>Welcome to Verbly AI, ${safeName}! 🎉</h1>
              <p>Your account has been successfully created using Google.</p>
              <p>We're excited to have you join us!</p>
              <h3>Explore Verbly AI</h3>
              <ul>
                <li>AI-powered website analysis</li>
                <li>Location Intelligence</li>
                <li>Website insights and recommendations</li>
                <li>Grammar checking</li>
              </ul>
              <p>Thank you for choosing Verbly AI.</p>
              <p><strong>Team Verbly AI</strong></p>
            </div>
          `,
        });

        if (emailError) {
          // Allow a later retry if email delivery failed.
          await admin
            .from("welcome_email_logs")
            .delete()
            .eq("user_id", user.id);

          console.error("Welcome email error:", emailError);
        } else {
          console.log("Welcome email accepted for:", user.email);
        }
      }
    } catch (emailError) {
      // Email failure should not prevent Google login.
      console.error("Welcome email setup failed:", emailError);
    }
  }

  let redirectPath = "/dashboard";

  if (next === "/dashboard") {
    redirectPath = "/dashboard";
  }

  return NextResponse.redirect(
    new URL(`/verbly-ai${redirectPath}`, request.url)
  );
}
