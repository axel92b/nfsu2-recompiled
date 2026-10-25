package com.nfsu2.androidevolved;

/** English UI messages for the Spanish text emitted by the pinned upstream native runtime. */
final class NativeMessages {
    private static final String[][] TEXT = {
        {"Datos accesibles: memoria interna/nfsu2", "Game data accessible: Internal storage/nfsu2"},
        {"Vulkan 1.1: presentación activa", "Vulkan 1.1: presentation active"},
        {"Arranque CRT pendiente", "CRT boot pending"},
        {"Ejecutando entrada CRT del juego…", "Running game CRT entry..."},
        {"Runtime guest ya inicializado", "Guest runtime already initialized"},
        {"Entrada guest terminada: ", "Guest entry finished: "},
        {"Arranque guest detenido: ", "Guest boot stopped: "},
        {"No se pudo cargar el driver Vulkan ", "Could not load Vulkan driver "},
        {". Elige el driver del sistema en el launcher.", ". Select the system driver in the launcher."},
        {"La GPU no pudo crear el dispositivo grafico (Vulkan, CreateDevice ",
                "The GPU could not create the graphics device (Vulkan, CreateDevice "},
        {"). Usa \"Probar driver\" en el launcher para ver que le falta.",
                "). Use \"Test driver\" in the launcher to see what is missing."},
        {"No se pudo abrir el driver seleccionado", "Could not open the selected driver"},
        {"El paquete no ofrece vkGetInstanceProcAddr", "The package does not provide vkGetInstanceProcAddr"},
        {"El paquete no ofrece vkCreateInstance", "The package does not provide vkCreateInstance"},
        {"Driver con funciones Vulkan incompletas", "The driver has incomplete Vulkan functions"},
        {"No se encontró una GPU Vulkan", "No Vulkan GPU found"}
    };

    private NativeMessages() {}

    static String toEnglish(String message) {
        for (String[] text : TEXT) message = message.replace(text[0], text[1]);
        return message
                .replaceAll("HLE pendiente: (\\S+) desde (\\S+)", "HLE pending: $1 from $2")
                .replaceAll("(ioctlsocket|Netbios) comando pendiente: (\\S+) desde (\\S+)",
                        "$1 command pending: $2 from $3")
                .replaceAll("(setsockopt|getsockopt) SOL_SOCKET opcion pendiente: (\\S+) desde (\\S+)",
                        "$1 SOL_SOCKET option pending: $2 from $3")
                .replaceAll("(setsockopt|getsockopt) nivel (\\S+) opcion (\\S+) pendiente desde (\\S+)",
                        "$1 level $2 option $3 pending from $4")
                .replaceAll("WSAIoctl solapado pendiente desde (\\S+)", "Overlapped WSAIoctl pending from $1")
                .replaceAll("WSAIoctl codigo pendiente: (\\S+) desde (\\S+)", "WSAIoctl code pending: $1 from $2")
                .replaceAll("ExitThread en el hilo principal desde (\\S+)", "ExitThread on the main thread from $1");
    }
}
