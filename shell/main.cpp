#include <saucer/webview.hpp>
#include "chrome.hpp"

#include <charconv>
#include <iostream>
#include <string>
#include <string_view>
#include <tuple>

#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#include <dwmapi.h>
#include <wrl/client.h>
#include <saucer/modules/stable/webview2.hpp>
#endif

void open_external(const saucer::url &url)
{
#ifdef _WIN32
    const auto text = url.string();
    const auto size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.c_str(), -1, nullptr, 0);
    if (!size)
        return;
    std::wstring wide(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.c_str(), -1, wide.data(), size);
    ShellExecuteW(nullptr, L"open", wide.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
#endif
}

#ifdef _WIN32
// Packaged layout: python\python.exe sits beside this exe. Start it hidden as the wiki server and read the
// loopback address it prints on its first line. It is tied to a job object, so it ends when this process does.
static HANDLE python_process = nullptr;

std::string start_bundled_python()
{
    wchar_t exe[MAX_PATH];
    const auto length = GetModuleFileNameW(nullptr, exe, MAX_PATH);
    if (!length || length >= MAX_PATH)
        return {};
    std::wstring dir(exe, length);
    dir.resize(dir.find_last_of(L'\\') + 1);
    const std::wstring python = dir + L"python\\python.exe";
    if (GetFileAttributesW(python.c_str()) == INVALID_FILE_ATTRIBUTES)
        return {};

    SECURITY_ATTRIBUTES inherit{sizeof(inherit), nullptr, TRUE};
    HANDLE read = nullptr, write = nullptr;
    if (!CreatePipe(&read, &write, &inherit, 0))
        return {};
    SetHandleInformation(read, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdOutput = write;
    startup.hStdError = write;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    std::wstring command = L"\"" + python + L"\" -m hydra_desktop --serve";
    PROCESS_INFORMATION info{};
    const BOOL started = CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE,
                                        CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr, dir.c_str(), &startup, &info);
    CloseHandle(write);
    if (!started)
    {
        CloseHandle(read);
        return {};
    }
    if (const auto job = CreateJobObjectW(nullptr, nullptr))
    {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits));
        AssignProcessToJobObject(job, info.hProcess);        // the job handle stays open until this process exits
    }
    ResumeThread(info.hThread);
    CloseHandle(info.hThread);
    python_process = info.hProcess;

    std::string line;
    char byte;
    DWORD got = 0;
    while (ReadFile(read, &byte, 1, &got, nullptr) && got == 1 && byte != '\n')
        if (byte != '\r')
            line += byte;
    CloseHandle(read);
    return line;
}
#endif

int main(int argc, char **argv)
{
    std::string address;
#ifdef _WIN32
    if (argc == 1)
    {
        address = start_bundled_python();
        if (address.empty())
        {
            std::cerr << "The bundled Python server did not start (no python folder beside the exe?).\n";
            return 2;
        }
    }
#endif
    if (address.empty() && (argc < 2 || argc > 3 || (argc == 3 && std::string_view(argv[2]) != "--smoke-test")))
    {
        std::cerr << "Start with python -m hydra_desktop ARCHIVE (this shell takes a local wiki URL).\n";
        return 2;
    }

    if (address.empty())
        address = argv[1];
    const auto origin = saucer::url::parse(address);
    if (!origin || origin->scheme() != "http" || origin->host() != "127.0.0.1" || !origin->port() ||
        origin->user() || origin->password())
    {
        std::cerr << "The desktop shell only opens a loopback Hydra wiki.\n";
        return 2;
    }

    auto app = saucer::application::create({.id = "org.openhydra.desktop", .argc = argc, .argv = argv});
    if (!app)
    {
        std::cerr << app.error().message() << '\n';
        return 1;
    }

    int result = 0;
    return app->run([&](saucer::application *application) -> coco::stray {
        auto created_window = saucer::window::create(application);
        if (!created_window)
        {
            std::cerr << created_window.error().message() << '\n';
            result = 1;
            application->quit();
            co_return;
        }
        auto window = created_window.value();
        auto created_view = saucer::webview::create({
            .window = window,
            .attributes = true,
#ifdef _WIN32
            .browser_flags = {"--enable-features=BackForwardCache"},
#endif
        });
        if (!created_view)
        {
            std::cerr << created_view.error().message() << '\n';
            result = 1;
            application->quit();
            co_return;
        }
        auto view = std::move(created_view).value();
#ifdef _WIN32
        Microsoft::WRL::ComPtr<ICoreWebView2Settings> settings;
        Microsoft::WRL::ComPtr<ICoreWebView2Settings9> regions;
        if (SUCCEEDED(view.native().webview->get_Settings(&settings)) && SUCCEEDED(settings.As(&regions)))
            regions->put_IsNonClientRegionSupportEnabled(TRUE);
#endif
        view.inject({.code = hydra_desktop_chrome, .run_at = saucer::script::time::creation, .clearable = false});
        window->set_decorations(saucer::window::decoration::partial);
        window->set_title("Hydra");
#ifdef _WIN32
        const auto module = GetModuleHandleW(nullptr);
        const auto hwnd = window->native().hwnd;
        for (const auto [kind, width, height] : {std::tuple{ICON_SMALL, SM_CXSMICON, SM_CYSMICON},
                                                 std::tuple{ICON_BIG, SM_CXICON, SM_CYICON}})
        {
            const auto icon = LoadImageW(module, MAKEINTRESOURCEW(1), IMAGE_ICON,
                                         GetSystemMetrics(width), GetSystemMetrics(height), LR_SHARED);
            if (icon)
                SendMessageW(hwnd, WM_SETICON, kind, reinterpret_cast<LPARAM>(icon));
        }
#endif
        window->set_size({1280, 900});
        window->set_min_size({800, 600});
        view.on<saucer::webview::event::navigate>([&](const saucer::navigation &navigation) {
            const auto target = navigation.url();
            if (target.scheme() == origin->scheme() && target.host() == origin->host() &&
                target.port() == origin->port() && !target.user() && !target.password())
                return saucer::policy::allow;
            if (navigation.user_initiated() && (target.scheme() == "https" || target.scheme() == "http") &&
                !target.user() && !target.password())
                open_external(target);
            return saucer::policy::block;
        });
        view.on<saucer::webview::event::title>([&](std::string_view title) {
            const auto text = title.ends_with("Hydra") ? std::string(title) : std::string(title) + " — Hydra";
            window->set_title(text.c_str());
        });
        view.on<saucer::webview::event::message>([&](std::string_view message) {
            constexpr std::string_view prefix = "hydra:chrome:";
            if (!message.starts_with(prefix) || message.size() != prefix.size() + 6)
                return saucer::status::unhandled;
            unsigned int rgb = 0;
            const auto parsed = std::from_chars(message.data() + prefix.size(), message.data() + message.size(), rgb, 16);
            if (parsed.ec != std::errc{} || parsed.ptr != message.data() + message.size())
                return saucer::status::unhandled;
            const saucer::color color{static_cast<std::uint8_t>(rgb >> 16), static_cast<std::uint8_t>(rgb >> 8),
                                      static_cast<std::uint8_t>(rgb), 255};
            window->set_background(color);
            view.set_background(color);
#ifdef _WIN32
            const COLORREF border = RGB(color.r, color.g, color.b);
            const BOOL dark = color.r * 299 + color.g * 587 + color.b * 114 < 128000;
            const auto hwnd = window->native().hwnd;
            DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, &border, sizeof(border));
            DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, &dark, sizeof(dark));
#endif
            return saucer::status::handled;
        });
        window->on<saucer::window::event::maximize>([&](bool maximized) {
            view.execute(maximized ? "dispatchEvent(new CustomEvent('hydra-window-maximized',{detail:true}))"
                                   : "dispatchEvent(new CustomEvent('hydra-window-maximized',{detail:false}))");
        });
        if (argc == 3)
        {
            view.on<saucer::webview::event::load>([&](saucer::state state) {
                if (state == saucer::state::finished)
                {
                    std::cout << "Hydra desktop: wiki loaded in WebView2\n";
                    application->quit();
                }
            });
        }
        view.set_url(address.c_str());
        window->show();
        co_await application->finish();
    }) || result;
}
