package com.example.antigrief;

import me.leoko.advancedban.bukkit.event.PunishmentEvent;
import me.leoko.advancedban.utils.PunishmentType;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.json.JSONObject;

import java.util.logging.Logger;

public class BanListener implements Listener {

    private final WebSocketClientManager clientManager;
    private final Logger logger;

    public BanListener(WebSocketClientManager clientManager, Logger logger) {
        this.clientManager = clientManager;
        this.logger = logger;
    }

    @EventHandler
    public void onPunishment(PunishmentEvent event) {
        PunishmentType type = event.getPunishment().getType();

        // We consider any type of ban as a confirmation of malicious activity.
        boolean isBan = type == PunishmentType.BAN ||
                        type == PunishmentType.TEMP_BAN ||
                        type == PunishmentType.IP_BAN;

        if (isBan) {
            String uuid = event.getPunishment().getUuid();
            String name = event.getPunishment().getName();

            // IP-Bans might not have a UUID if the player was never on the server.
            // We need the UUID to correlate data, so we ignore these.
            if (uuid == null || uuid.isEmpty()) {
                logger.warning("A ban occurred without a player UUID. Cannot send feedback.");
                return;
            }

            logger.info("Detected ban for player " + name + ". Sending confirmation to Python server.");

            JSONObject confirmationData = new JSONObject();
            confirmationData.put("type", "grief_confirmation");
            confirmationData.put("playerUUID", uuid);
            confirmationData.put("playerName", name);
            confirmationData.put("reason", event.getPunishment().getReason());
            confirmationData.put("operator", event.getPunishment().getOperator());
            confirmationData.put("punishmentType", type.name());


            clientManager.sendEventData(confirmationData);
        }
    }
}
