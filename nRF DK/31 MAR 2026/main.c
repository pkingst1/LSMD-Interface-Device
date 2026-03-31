#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/ring_buffer.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>
#include <bluetooth/services/nus.h>
#include <zephyr/settings/settings.h>
 
#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)
 
// NUS MTU max payload is 244 (247 L2CAP MTU - 3 bytes for ATT header)
#define NUS_MAX_PAYLOAD 244 
#define RING_BUF_SIZE 2048
 
static struct bt_conn *current_conn;
static const struct device *uart = DEVICE_DT_GET(DT_NODELABEL(uart0));
static const struct gpio_dt_spec adv_btn = GPIO_DT_SPEC_GET(DT_ALIAS(adv_btn), gpios);
 
// Ring buffer and thread synchronization
RING_BUF_DECLARE(uart_rx_ringbuf, RING_BUF_SIZE);
K_SEM_DEFINE(ble_tx_sem, 0, 1);
K_THREAD_STACK_DEFINE(ble_tx_thread_stack, 1024);
static struct k_thread ble_tx_thread_data;
 
// BLE Advertising Data
static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};
 
static const struct bt_data sd[] = {
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_NUS_VAL),
};
 
// ==========================================
// MTU Exchange (file-scope so it persists
// through the async exchange process)
// ==========================================
static void mtu_exchange_cb(struct bt_conn *conn, uint8_t err,
                            struct bt_gatt_exchange_params *params) {
    if (err) {
        printk("MTU exchange failed (err %u)\n", err);
    } else {
        printk("MTU exchange successful\n");
    }
}
 
static struct bt_gatt_exchange_params mtu_params = {
    .func = mtu_exchange_cb,
};
 
// ==========================================
// THREAD: Process UART data and send over BLE
// ==========================================
void ble_tx_thread(void *p1, void *p2, void *p3) {
    uint8_t tx_buf[NUS_MAX_PAYLOAD];
 
    while (1) {
        // Wait until there is data in the ring buffer
        k_sem_take(&ble_tx_sem, K_FOREVER);
 
        if (!current_conn) continue;
 
        uint32_t len = ring_buf_get(&uart_rx_ringbuf, tx_buf, sizeof(tx_buf));
        if (len > 0) {
            int err;
            do {
                err = bt_nus_send(current_conn, tx_buf, len);
                // If the TX queue is full, wait 5ms and retry. Do NOT drop the data.
                if (err == -ENOMEM || err == -EAGAIN) {
                    k_sleep(K_MSEC(5));
                } else if (err) {
                    printk("Failed to send data over BLE (err %d)\n", err);
                    break; 
                }
            } while (err == -ENOMEM || err == -EAGAIN);
        }
 
        // If there's still data left in the ring buffer, trigger the thread again
        if (!ring_buf_is_empty(&uart_rx_ringbuf)) {
            k_sem_give(&ble_tx_sem);
        }
    }
}
 
// ==========================================
// UART: Receive from PIC32 / Send to PIC32
// ==========================================
static void uart_cb(const struct device *dev, void *user_data) {
    if (!device_is_ready(dev)) return;
 
    uart_irq_update(dev);
 
    // RX: Data coming from PIC32 -> Put in Ring Buffer -> Signal BLE TX Thread
    if (uart_irq_rx_ready(dev)) {
        uint8_t buffer[64];
        int len = uart_fifo_read(dev, buffer, sizeof(buffer));
        if (len > 0) {
            ring_buf_put(&uart_rx_ringbuf, buffer, len);
            k_sem_give(&ble_tx_sem);
        }
    }
}
 
// NUS Callback: Data coming from App -> Send to PIC32
static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data, uint16_t len) {
    char debug_buf[64];
    uint16_t copy_len = (len < sizeof(debug_buf) - 1) ? len : (sizeof(debug_buf) - 1);
    memcpy(debug_buf, data, copy_len);
    debug_buf[copy_len] = '\0'; 
    
    // Forward the data to the PIC32
    for (uint16_t i = 0; i < len; i++) {
        uart_poll_out(uart, data[i]);
    }
    
    // --- THE FIX: Inject a newline if the app didn't send one ---
    if (len > 0 && data[len - 1] != '\n' && data[len - 1] != '\r') {
        uart_poll_out(uart, '\r'); // Carriage Return
        uart_poll_out(uart, '\n'); // Line Feed
    }
    // ------------------------------------------------------------
}
 
static struct bt_nus_cb nus_cb = {
    .received = bt_receive_cb,
};
 
// ==========================================
// BLE: Connection & Security Setup
// ==========================================
static void connected(struct bt_conn *conn, uint8_t err) {
    if (err) {
        printk("Connection failed (err %u)\n", err);
        return;
    }
    current_conn = bt_conn_ref(conn);
    printk("Connected\n");
 
    // Request MTU 247 from the peripheral side.
    // mtu_params is file-scope so it persists through the async exchange.
    bt_gatt_exchange_mtu(conn, &mtu_params);
 
    // Require Level 4 Security (Authenticated LE Secure Connections)
    if (bt_conn_set_security(conn, BT_SECURITY_L4)) {
        printk("Failed to set security\n");
    }
}
 
static void disconnected(struct bt_conn *conn, uint8_t reason) {
    printk("Disconnected (reason %u)\n", reason);
    if (current_conn) {
        bt_conn_unref(current_conn);
        current_conn = NULL;
    }
}
 
BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected    = connected,
    .disconnected = disconnected,
};
 
// Satisfy Secure BLE display requirement for hard-coded passkey
static void auth_passkey_display(struct bt_conn *conn, unsigned int passkey) {
    printk("Passkey for pairing: %06u\n", passkey);
}
 
static void auth_cancel(struct bt_conn *conn) {
    printk("Pairing canceled\n");
}
 
static struct bt_conn_auth_cb auth_cb_display = {
    .passkey_display = auth_passkey_display,
    .cancel = auth_cancel,
};
 
// ==========================================
// BUTTON: Advertise Trigger
// ==========================================
static void start_advertising(struct k_work *work) {
    if (current_conn) {
        printk("Already connected. Ignoring advertise request.\n");
        return;
    }
 
    int err = bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
    if (err) {
        if (err == -EALREADY) {
            printk("Already advertising.\n");
        } else {
            printk("Advertising failed to start (err %d)\n", err);
        }
    } else {
        printk("Advertising successfully started\n");
    }
}
K_WORK_DEFINE(adv_work, start_advertising);
 
static void button_pressed_cb(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    k_work_submit(&adv_work);
}
static struct gpio_callback button_cb_data;
 
// ==========================================
// MAIN INITIALIZATION
// ==========================================
int main(void) {
    int err;
 
    // 1. Setup UART
    if (!device_is_ready(uart)) {
        printk("UART device not ready\n");
        return 0;
    }
    uart_irq_callback_set(uart, uart_cb);
    uart_irq_rx_enable(uart);
 
    // 2. Setup Button
    if (device_is_ready(adv_btn.port)) {
        gpio_pin_configure_dt(&adv_btn, GPIO_INPUT);
        gpio_pin_interrupt_configure_dt(&adv_btn, GPIO_INT_EDGE_TO_ACTIVE);
        gpio_init_callback(&button_cb_data, button_pressed_cb, BIT(adv_btn.pin));
        gpio_add_callback(adv_btn.port, &button_cb_data);
    }
 
    // 3. Setup BLE Authentication (Hard-coded Passkey)
    bt_conn_auth_cb_register(&auth_cb_display);
    bt_passkey_set(123456);
 
    // 4. Initialize Bluetooth
    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed (err %d)\n", err);
        return 0;
    }
 // Load the saved bonding keys from flash memory
    settings_load(); 
    // ---------------------

    // 5. Initialize NUS Service
    err = bt_nus_init(&nus_cb);
    if (err) {
        printk("Failed to initialize NUS (err: %d)\n", err);
        return 0;
    }
 
    // 6. Start the BLE TX Thread
    k_thread_create(&ble_tx_thread_data, ble_tx_thread_stack,
                    K_THREAD_STACK_SIZEOF(ble_tx_thread_stack),
                    ble_tx_thread, NULL, NULL, NULL,
                    7, 0, K_NO_WAIT);
 
    printk("nRF52 LSMD-DIU initialized and in IDLE state.\n");
    printk("Press Button (P0.13) to advertise.\n");
 
    return 0;
}