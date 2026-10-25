package com.nfsu2.androidevolved;

public final class NativeMessagesCheck {
    private static void check(String original, String expected) {
        String actual = NativeMessages.toEnglish(original);
        if (!expected.equals(actual))
            throw new AssertionError("Expected: " + expected + "\nActual: " + actual);
        if (!actual.equals(NativeMessages.toEnglish(actual)))
            throw new AssertionError("English messages must remain unchanged");
    }

    public static void main(String[] args) {
        check("Datos accesibles: memoria interna/nfsu2\nVulkan 1.1: presentación activa\nEjecutando entrada CRT del juego…",
                "Game data accessible: Internal storage/nfsu2\nVulkan 1.1: presentation active\nRunning game CRT entry...");
        check("Arranque CRT pendiente", "CRT boot pending");
        check("Runtime guest ya inicializado", "Guest runtime already initialized");
        check("Entrada guest terminada: 0", "Guest entry finished: 0");
        check("Arranque guest detenido: HLE pendiente: CreateFileA desde 0x401000",
                "Guest boot stopped: HLE pending: CreateFileA from 0x401000");
        check("No se pudo cargar el driver Vulkan libvulkan_test.so. Elige el driver del sistema en el launcher.",
                "Could not load Vulkan driver libvulkan_test.so. Select the system driver in the launcher.");
        check("La GPU no pudo crear el dispositivo grafico (Vulkan, CreateDevice 123). Usa \"Probar driver\" en el launcher para ver que le falta.",
                "The GPU could not create the graphics device (Vulkan, CreateDevice 123). Use \"Test driver\" in the launcher to see what is missing.");
        check("No se pudo abrir el driver seleccionado", "Could not open the selected driver");
        check("El paquete no ofrece vkGetInstanceProcAddr", "The package does not provide vkGetInstanceProcAddr");
        check("El paquete no ofrece vkCreateInstance", "The package does not provide vkCreateInstance");
        check("Driver con funciones Vulkan incompletas", "The driver has incomplete Vulkan functions");
        check("No se encontró una GPU Vulkan", "No Vulkan GPU found");
        check("ioctlsocket comando pendiente: 0x20 desde 0x401000",
                "ioctlsocket command pending: 0x20 from 0x401000");
        check("Netbios comando pendiente: 0x20 desde 0x401000",
                "Netbios command pending: 0x20 from 0x401000");
        for (String function : new String[] {"setsockopt", "getsockopt"}) {
            check(function + " SOL_SOCKET opcion pendiente: 0x20 desde 0x401000",
                    function + " SOL_SOCKET option pending: 0x20 from 0x401000");
            check(function + " nivel 0x1 opcion 0x20 pendiente desde 0x401000",
                    function + " level 0x1 option 0x20 pending from 0x401000");
        }
        check("WSAIoctl solapado pendiente desde 0x401000", "Overlapped WSAIoctl pending from 0x401000");
        check("WSAIoctl codigo pendiente: 0x20 desde 0x401000", "WSAIoctl code pending: 0x20 from 0x401000");
        check("ExitThread en el hilo principal desde 0x401000", "ExitThread on the main thread from 0x401000");
        check("Cannot read Internal storage/nfsu2/SPEED2.EXE; check files and storage permission",
                "Cannot read Internal storage/nfsu2/SPEED2.EXE; check files and storage permission");
        check("/storage/emulated/0/nfsu2/LANGUAGES/Spanish.bin",
                "/storage/emulated/0/nfsu2/LANGUAGES/Spanish.bin");
        check("English UK", "English UK");
        check("Some unknown native error", "Some unknown native error");
        System.out.println("Native message translation checks passed.");
    }
}
