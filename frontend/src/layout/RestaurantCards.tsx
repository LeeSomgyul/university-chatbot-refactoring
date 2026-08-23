interface Restaurant {
    name: string;
    address: string;
    url: string;
    phone: string;
    category: string;
}

interface RestaurantCardsProps {
    restaurants: Restaurant[];
}

export const RestaurantCards = ({ restaurants  }: RestaurantCardsProps) => {
    if (!restaurants || restaurants.length === 0) return null

    return (
        <div className="restaurant-cards">
            {restaurants.map((r, idx) => (
                <a
                    key={idx}
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center mt-3 mb-1 gap-3 px-10 py-3.5 rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-0.5 hover:border-[#BADDFE] transition-all duration-150"
                >
                    <div className="flex-shrink-0 w-10 h-10 bg-[#BADDFE] flex items-center justify-center text-xl rounded-xl">
                        🍽️
                    </div>
                    <div className="flex-1 min-w-0 mb-1">
                        <div className="flex items-center gap-2">
                            <div className="text-lg font-bold text-[#004C97] truncate">
                                {r.name}
                            </div>
                            <div className="text-sm bg-gray-200 rounded-lg px-1">
                                {r.category}
                            </div>
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5 truncate">
                            {r.address}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5 truncate">
                            {r.phone}
                        </div>
                        <div className="text-xs font-semibold text-gray-500 mt-1">
                            자세히 보기 →
                        </div>
                    </div>
                </a>
            ))}
        </div>
    )
}