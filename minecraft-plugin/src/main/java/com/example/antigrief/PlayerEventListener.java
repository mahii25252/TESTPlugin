package com.example.antigrief;

import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.json.JSONObject;

import java.time.Instant;

public class PlayerEventListener implements Listener {

    private final WebSocketClientManager clientManager;

    public PlayerEventListener(WebSocketClientManager clientManager) {
        this.clientManager = clientManager;
    }

    private JSONObject createBaseEventData(Player player, String eventType) {
        JSONObject data = new JSONObject();
        data.put("timestamp", Instant.now().toString());
        data.put("eventType", eventType);
        data.put("playerUUID", player.getUniqueId().toString());
        data.put("playerName", player.getName());

        Location loc = player.getLocation();
        JSONObject locationData = new JSONObject();
        locationData.put("world", loc.getWorld().getName());
        locationData.put("x", loc.getX());
        locationData.put("y", loc.getY());
        locationData.put("z", loc.getZ());
        data.put("playerLocation", locationData);

        return data;
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerMove(PlayerMoveEvent event) {
        if (event.getFrom().getBlockX() != event.getTo().getBlockX() ||
            event.getFrom().getBlockY() != event.getTo().getBlockY() ||
            event.getFrom().getBlockZ() != event.getTo().getBlockZ()) {

            JSONObject data = createBaseEventData(event.getPlayer(), "PlayerMove");
            clientManager.sendEventData(data);
        }
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBlockBreak(BlockBreakEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "BlockBreak");

        Location loc = event.getBlock().getLocation();
        JSONObject blockData = new JSONObject();
        blockData.put("type", event.getBlock().getType().toString());
        blockData.put("world", loc.getWorld().getName());
        blockData.put("x", loc.getBlockX());
        blockData.put("y", loc.getBlockY());
        blockData.put("z", loc.getBlockZ());
        data.put("block", blockData);

        clientManager.sendEventData(data);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onBlockPlace(BlockPlaceEvent event) {
        JSONObject data = createBaseEventData(event.getPlayer(), "BlockPlace");

        Location loc = event.getBlock().getLocation();
        JSONObject blockData = new JSONObject();
        blockData.put("type", event.getBlock().getType().toString());
        blockData.put("world", loc.getWorld().getName());
        blockData.put("x", loc.getBlockX());
        blockData.put("y", loc.getBlockY());
        blockData.put("z", loc.getBlockZ());
        data.put("block", blockData);

        clientManager.sendEventData(data);
    }
}
