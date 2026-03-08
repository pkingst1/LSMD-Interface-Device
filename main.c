#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <bluetooth/services/nus.h>
#include <SEGGER_RTT.h> // ADDED: Native RTT Library
#include <string.h>

/* --- Hardware Setup --- */
#define SW0_NODE DT_ALIAS(sw0)
static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(SW0_NODE, gpios);
static struct gpio_callback button_cb_data;

#define LED0_NODE DT_ALIAS(led0)
static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED0_NODE, gpios);

static const struct device *uart = DEVICE_DT_GET(DT_NODELABEL(uart0));
static struct bt_conn *current_conn;

/* --- LED Blink Timer --- */
static void blink_timer_handler(struct k_timer *timer_id) {
    gpio_pin_toggle_dt(&led);
}
K_TIMER_DEFINE(blink_timer, blink_timer_handler, NULL);

/* --- BLE Advertising Data --- */
static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_NUS_VAL),
};

/* --- BLE Connection Handling --- */
static void connected(struct bt_conn *conn, uint8_t err) {
    if (err) return;
    current_conn = bt_conn_ref(conn);
    k_timer_stop(&blink_timer);
    gpio_pin_set_dt(&led, 1); 
    printk("\n[STATUS] Connected to PC/Mobile!\n");
}

static void disconnected(struct bt_conn *conn, uint8_t reason) {
    if (current_conn) {
        bt_conn_unref(current_conn);
        current_conn = NULL;
    }
    gpio_pin_set_dt(&led, 0);
    printk("\n[STATUS] Disconnected.\n");
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
};

/* --- PIPELINE 1: PC (BLE) -> nRF -> PIC32 --- */
static void bt_receive_cb(struct bt_conn *conn, const void *data, uint16_t len, void *user_data) {
    const uint8_t *bytes = (const uint8_t *)data;
    
    printk("[BLE -> PIC32]: %.*s\n", len, bytes);
    
    for (uint16_t i = 0; i < len; i++) {
        uart_poll_out(uart, bytes[i]);
    }
}
static struct bt_nus_cb nus_cb = { .received = bt_receive_cb };

/* --- PIPELINE 2: PIC32 -> nRF -> PC (BLE) --- */
static void uart_isr(const struct device *dev, void *user_data) {
    uart_irq_update(dev);
    
    if (uart_irq_rx_ready(dev)) {
        uint8_t rx_buffer[64];
        int recv_len = uart_fifo_read(dev, rx_buffer, sizeof(rx_buffer));
        
        if (recv_len > 0) {
            printk("[PIC32 -> BLE]: %.*s", recv_len, rx_buffer);
            
            if (current_conn) {
                bt_nus_send(current_conn, rx_buffer, recv_len);
            }
        }
    }
}

/* --- PIPELINE 3: RTT Injection -> PIC32 --- */
static void rtt_input_thread(void) {
    char rx_buf[64];
    int rx_idx = 0;

    while (1) {
        char c;
        // Read 1 byte from the RTT buffer without blocking
        if (SEGGER_RTT_Read(0, &c, 1) > 0) {
            
            // LIVE ECHO: Instantly print the character back to the terminal
            // so you can physically see that the DK received it!
            printk("%c", c);

            // Check if user pressed Enter (newline or carriage return)
            if (c == '\n' || c == '\r') {
                if (rx_idx > 0) {
                    rx_buf[rx_idx] = '\0'; // Null-terminate the string
                    
                    printk("\n[RTT INJECTION -> PIC32]: %s\n", rx_buf);
                    
                    // Push characters directly out the UART TX pin
                    for (int i = 0; i < rx_idx; i++) {
                        uart_poll_out(uart, rx_buf[i]);
                    }
                    rx_idx = 0; // Reset buffer for next command
                }
            } 
            // Store normal characters
            else if (rx_idx < sizeof(rx_buf) - 1) {
                rx_buf[rx_idx++] = c;
            }
        } else {
            // Yield the thread to save power if no keys are being pressed
            k_msleep(50); 
        }
    }
}
K_THREAD_DEFINE(rtt_thread_id, 1024, rtt_input_thread, NULL, NULL, NULL, 7, 0, 0);

/* --- Work Queue for Advertising --- */
static struct k_work adv_work;

static void adv_work_handler(struct k_work *work) {
    k_timer_start(&blink_timer, K_NO_WAIT, K_MSEC(500));
    // FIXED: Updated deprecated macro to the modern standard
    bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), NULL, 0);
    printk("\n[STATUS] Advertising Started. Waiting for connection...\n");
}

/* --- Button Trigger --- */
void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    k_work_submit(&adv_work);
}

/* --- Main Initialization --- */
int main(void) {
    int err;

    if (!gpio_is_ready_dt(&button)) return 0;
    gpio_pin_configure_dt(&button, GPIO_INPUT);
    gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);
    gpio_init_callback(&button_cb_data, button_pressed, BIT(button.pin));
    gpio_add_callback(button.port, &button_cb_data);

    if (!gpio_is_ready_dt(&led)) return 0;
    gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE);

    if (!device_is_ready(uart)) return 0;
    uart_irq_callback_set(uart, uart_isr);
    uart_irq_rx_enable(uart);

    k_work_init(&adv_work, adv_work_handler);

    err = bt_enable(NULL);
    if (err) return 0;
    
    err = bt_nus_init(&nus_cb);
    if (err) return 0;

    printk("[STATUS] Bridge Ready. Type commands and press Enter to inject to PIC32, or press Button 1 to advertise.\n");

    while (1) {
        k_msleep(1000);
    }
    return 0;
}