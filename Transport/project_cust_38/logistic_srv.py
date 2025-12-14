def reliable_send(conn, data: bytes) -> None:
    """
    Функция отправки данных в сокет
    Обратите внимание, что данные ожидаются сразу типа bytes
    """
    # Разбиваем передаваемые данные на куски максимальной длины 0xffff (65535)
    try:
        for chunk in (data[_:_ + 0xffff] for _ in range(0, len(data), 0xffff)):
            conn.send(len(chunk).to_bytes(2, "big"))  # Отправляем длину куска (2 байта)
            conn.send(chunk)  # Отправляем сам кусок
    except:
        conn.send(b"\x00\x00")
    conn.send(b"\x00\x00")  # Обозначаем конец передачи куском нулевой длины


def reliable_receive(UDPClientSocket) -> bytes:
    def readexactly(bytes_count: int, UDPClientSocket) -> bytes:
        """
        Функция приёма определённого количества байт
        """
        b = b''
        while len(b) < bytes_count:  # Пока не получили нужное количество байт
            part = UDPClientSocket.recv(bytes_count - len(b))  # Получаем оставшиеся байты
            if not part:  # Если из сокета ничего не пришло, значит его закрыли с другой стороны
                print("Соединение потеряно")
                return
            b += part
        return b

    """
    Функция приёма данных
    Обратите внимание, что возвращает тип bytes
    """
    b = b''
    while True:
        try:
            part = readexactly(2, UDPClientSocket)
            if part == None:
                return b
            part_len = int.from_bytes(part, "big")  # Определяем длину ожидаемого куска
            if part_len == 0 or part_len == None:  # Если пришёл кусок нулевой длины, то приём окончен
                return b
        except:
            return b
        try:
            b += readexactly(part_len, UDPClientSocket)  # Считываем сам кусок
        except:
            return
