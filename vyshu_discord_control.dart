// vyshu_discord_control.dart
// Add this to your Vyshu AI Flutter app (lib/) to control the Discord bot.
// Requires the `http` package in pubspec.yaml:  http: ^1.2.0

import 'dart:convert';
import 'package:http/http.dart' as http;

class VyshuDiscordControl {
  // Point this at wherever the bot is hosted (Oracle VM IP, domain, etc.)
  // e.g. "http://123.45.67.89:8080" or "https://vyshu-bot.yourdomain.com"
  final String baseUrl;
  final String apiKey; // must match API_SECRET_KEY in the bot's .env

  VyshuDiscordControl({required this.baseUrl, required this.apiKey});

  Map<String, String> get _headers => {
        "X-API-Key": apiKey,
        "Content-Type": "application/json",
      };

  /// Returns bot online status + every server's current mode.
  Future<Map<String, dynamic>> getStatus() async {
    final res = await http.get(Uri.parse("$baseUrl/api/status"), headers: _headers);
    if (res.statusCode != 200) {
      throw Exception("Failed to get status: ${res.statusCode} ${res.body}");
    }
    return jsonDecode(res.body);
  }

  /// Change a server's mode: "translate" | "personal" | "off"
  Future<void> setMode({required String guildId, required String mode}) async {
    final res = await http.post(
      Uri.parse("$baseUrl/api/mode"),
      headers: _headers,
      body: jsonEncode({"guild_id": guildId, "mode": mode}),
    );
    if (res.statusCode != 200) {
      throw Exception("Failed to set mode: ${res.statusCode} ${res.body}");
    }
  }

  /// Quick unauthenticated ping to check if the bot's host is reachable at all.
  Future<bool> ping() async {
    try {
      final res = await http.get(Uri.parse("$baseUrl/api/health"));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

// Example usage inside a widget:
//
// final control = VyshuDiscordControl(
//   baseUrl: "http://YOUR_BOT_HOST:8080",
//   apiKey: "same_value_as_API_SECRET_KEY",
// );
//
// final status = await control.getStatus();
// print(status["servers"]); // list of {id, name, mode}
//
// await control.setMode(guildId: "123456789", mode: "personal");
