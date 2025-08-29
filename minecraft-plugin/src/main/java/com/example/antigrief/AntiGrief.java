package com.example.antigrief;

import org.bukkit.plugin.java.JavaPlugin;

public class AntiGrief extends JavaPlugin {

    private WebSocketClientManager clientManager;
    private String serverId;

    @Override
    public void onEnable() {
        getLogger().info("AntiGrief plugin is enabling...");

        saveDefaultConfig();

        // Use the seed of the main world as the server identifier
        if (!getServer().getWorlds().isEmpty()) {
            this.serverId = String.valueOf(getServer().getWorlds().get(0).getSeed());
        } else {
            getLogger().warning("No worlds found. Using a default server ID.");
            this.serverId = "default-server-id";
        }

        getLogger().info("This server's ID is: " + this.serverId);

        String wsUrl = getConfig().getString("websocket-url", "ws://localhost:8765");

        try {
            clientManager = new WebSocketClientManager(this, wsUrl, serverId);
            clientManager.connect();

            // Register event listeners
            getServer().getPluginManager().registerEvents(new PlayerEventListener(clientManager), this);

            // Register listener for AdvancedBan if it's present
            if (getServer().getPluginManager().getPlugin("AdvancedBan") != null) {
                getLogger().info("AdvancedBan found, registering ban listener for feedback loop.");
                getServer().getPluginManager().registerEvents(new BanListener(clientManager, getLogger()), this);
            } else {
                getLogger().info("AdvancedBan not found. The feedback loop feature will be disabled.");
            }

            getLogger().info("AntiGrief plugin has been enabled successfully.");
        } catch (Exception e) {
            getLogger().severe("Failed to initialize WebSocket client: " + e.getMessage());
            e.printStackTrace();
            getServer().getPluginManager().disablePlugin(this);
        }
    }

    @Override
    public void onDisable() {
        if (clientManager != null) {
            clientManager.close();
        }
        getLogger().info("AntiGrief plugin has been disabled.");
    }
}
