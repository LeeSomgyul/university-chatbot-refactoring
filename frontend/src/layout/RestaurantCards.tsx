interface Restaurant {
    name: string;
    address: string;
    url: string;
    phone: string;
    category: string;
    review_summary?: string | null;
}

interface RestaurantCardsProps {
    restaurants: Restaurant[];
    onWriteReview: (restaurant: Restaurant)=> void;
}

export const RestaurantCards = ({ restaurants, onWriteReview  }: RestaurantCardsProps) => {
    if (!restaurants || restaurants.length === 0) return null

    return (
        <div className="">
            {restaurants.map((r, idx) => (
                <div className="flex flex-col">
                    <a
                        key={idx}
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center mt-3 mb-1 gap-3 px-10 py-3.5 rounded-2xl bg-white border border-gray-100 shadow-sm hover:border-[#BADDFE] transition-all duration-150"
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
                            {r.review_summary && (
                                <div>
                                    <p className="text-sm text-gray-500 mt-3">재학생들의 리뷰를 통합 요약한 내용입니다.</p>
                                    <div className="text-[#004C97] text-sm font-semibold">
                                        {r.review_summary}
                                    </div>
                                </div>
                            )}
                            <div className="text-xs font-semibold text-gray-500 mt-1">
                                자세히 보기 →
                            </div>
                        </div>
                    </a>
                    <div className="text-right">
                        <button onClick={()=>onWriteReview(r)} className="cursor-pointer text-xs text-[#004C97] underline ml-2">
                            리뷰 남기기
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
}