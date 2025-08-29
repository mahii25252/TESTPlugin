package com.example.antigrief;

import org.bukkit.Bukkit;
import org.json.JSONObject;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.HashMap;
import java.util.Map;

public class WebSocketClientManager {

    private final AntiGrief plugin;
    private WebSocketClient client;
    private final String serverId;
    private final String url;

    public WebSocketClientManager(AntiGrief plugin, String url, String serverId) {
        this.plugin = plugin;
        this.url = url;
        this.serverId = serverId;
    }

    public void connect() throws URISyntaxException {
        Map<String, String> headers = new HashMap<>();
        headers.put("Server-ID", this.serverId);

        this.client = new WebSocketClient(new URI(url), headers) {
            @Override
            public void onOpen(ServerHandshake handshakedata) {
                plugin.getLogger().info("Successfully connected to the Python WebSocket server.");
            }

            @Override
            public void onMessage(String message) {
                // Run in main thread to interact with Bukkit API
                Bukkit.getScheduler().runTask(plugin, () -> {
                    plugin.getLogger().info("Received message from Python: " + message);
                    // In Phase 2, this will handle alerts.
                    // For now, we can just log it.
                    // Example of handling an alert:
                    try {
                        JSONObject json = new JSONObject(message);
                        if ("grief_alert".equals(json.optString("type"))) {
                            String playerName = json.getString("player");
                            String reason = json.getString("reason");
                            String location = json.getString("location");
                            String alertMessage = String.format("§c[AntiGrief Alert] §ePlayer %s might be griefing. §fReason: %s §7at %s", playerName, reason, location);

                            Bukkit.getOnlinePlayers().forEach(player -> {
                                if (player.isOp()) {
                                    player.sendMessage(alertMessage);
                                }
                            });
                        }
                    } catch (Exception e) {
                        plugin.getLogger().warning("Failed to parse message from Python: " + message);
                    }
                });
            }

            @Override
            public void onClose(int code, String reason, boolean remote) {
                plugin.getLogger().warning("Disconnected from Python WebSocket server. Reason: " + (reason.isEmpty() ? "Unknown" : reason));
                // Optional: attempt to reconnect
            }

            @Override
            public void onError(Exception ex) {
                plugin.getLogger().severe("A WebSocket error occurred: " + ex.getMessage());
            }
        };

        plugin.getLogger().info("Attempting to connect to WebSocket server at " + url);
        this.client.connect();
    }

    public void close() {
        if (client != null) {
            client.close();
        }
    }

    public void sendEventData(JSONObject data) {
        if (client != null && client.isOpen()) {
            client.send(data.toString());
        } else {
            // Maybe queue the data or log a warning
            plugin.getLogger().warning("Cannot send event data, WebSocket is not connected.");
        }
    }
}
